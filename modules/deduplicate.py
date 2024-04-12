from typing import List
from openai import OpenAI
from pydantic import BaseModel
from sklearn.cluster import DBSCAN
import numpy as np
import json
from prisma import Prisma
from prisma.models import DeduplicatedCard, ValuesCard
from prisma.enums import ProcessState
from tqdm import tqdm
from gpt import gpt4
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

from prompt_segments import attentional_policy_definition


class ClusterableObject(BaseModel):
    id: int
    embedding: List[float]


class CardWithDistance(DeduplicatedCard):
    distance: float


db = Prisma()
client = OpenAI()

guidelines = """
# Guidelines
Two or more values cards are about the same value if:
- A user that articulated one of the cards would feel like the other cards in the cluster capture what they cared about *fully*.
- Someone instructed to pay attention to one set of attention policies would pay attention to exactly the same things as someone instructed to pay attention to the other set.
- Any difference in attention policies between the cards would be acknowledged as an oversight or a mistake, and both cards should be updated to reflect the same attention policies.
- The cards are formulated using roughly the same level of granularity and detail.

Only if the cards pass all of these criteria can they be considered to be about the same value.
"""

dedupe_prompt = f"""
You are given a values cards and a list of other canonical values cards. Determine if the value in the input values card is already represented by one of the canonical values. If so, return the id of the canonical values card that represents the source of meaning.

{guidelines}
"""

best_values_card_prompt = f"""
You will be provided with a list of "values cards", all representing the same value. Your task is to return the "id" of the "values card" which has the best attentional policies, according to the guidelines below.

{attentional_policy_definition}
"""

dedupe_function = {
    "name": "dedupe",
    "description": "Return the id of the canonical values card that is a duplicate value ",
    "parameters": {
        "type": "object",
        "properties": {
            "canonical_card_id": {
                "type": "number",
                "description": "The id of the canonical values card that is about the same source of meaning as the provided non-canonical values card. Should only be included if such a card exists.",
            },
        },
    },
}

best_function = {
    "name": "best_card",
    "description": "Return the best formulated values card from a list of values cards.",
    "parameters": {
        "type": "object",
        "properties": {
            "best_values_card_id": {
                "type": "integer",
                "description": "The id of the values card that is best formulated according to the guidelines.",
            },
        },
        "required": ["best_values_card_id"],
    },
}


def _embed_card(card: ValuesCard | DeduplicatedCard) -> List[float]:
    text = (
        "It feels meaningful to pay attention to the following in choices:\n"
        + "\n".join(card.policies)
    )  # TODO - include something about choice type.
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding


def _similarity_search(
    candidate: ValuesCard, deduplication_id: int, limit: int = 5, threshold: float = 0.1
) -> List[DeduplicatedCard]:
    # get embeddings from db
    query = f"""SELECT id, embedding::real[] FROM "ValuesCard" WHERE id = {candidate.id} AND embedding IS NOT NULL;"""
    result = db.query_raw(query, model=ClusterableObject)
    embeddings = result[0].embedding

    # search for similar cards
    query = f"""SELECT DISTINCT c.id, c.title, c.policies, c."createdAt", c."updatedAt", c."deduplicationId", c.embedding <=> '{json.dumps(embeddings)}'::vector as "distance" FROM "DeduplicatedCard" c WHERE "deduplicationId" = {deduplication_id} AND "embedding" IS NOT NULL ORDER BY "distance" ASC LIMIT {limit};"""
    result = db.query_raw(query, model=CardWithDistance)

    return [r for r in result if r.distance < threshold]


def _cluster(objects: List[ClusterableObject]):
    embeddings = np.array([obj.embedding for obj in objects])
    distance_matrix = cosine_distances(embeddings)

    # Run DBSCAN
    clustering = DBSCAN(eps=0.11, min_samples=3, metric="precomputed").fit(
        distance_matrix
    )

    # Group the objects into clusters based on the labels
    labels_to_objs = {}
    for label, obj in zip(clustering.labels_, objects):
        if label == -1:
            continue
        if label not in labels_to_objs:
            labels_to_objs[label] = []
        labels_to_objs[label].append(obj)

    # Convert the dictionary values to a list of lists for the clustered objects
    return list(labels_to_objs.values())


def _fetch_similar_deduplicated_card(
    candidate: ValuesCard, deduplication_id: int
) -> DeduplicatedCard | None:
    similar_cards = _similarity_search(candidate, deduplication_id)
    if not similar_cards:
        return None
    user_prompt = json.dumps(
        {
            "input_values_card": {"policies": candidate.policies},
            "canonical_values_cards": [
                {"id": c.id, "policies": c.policies} for c in similar_cards
            ],
        }
    )
    response = gpt4(user_prompt, dedupe_prompt, function=dedupe_function)
    assert isinstance(response, dict)
    matching_id = response["canonical_card_id"]
    return next((c for c in similar_cards if c.id == matching_id), None)


def _get_representative(card_ids: List[int]):
    cards = db.valuescard.find_many(where={"id": {"in": card_ids}})
    if len(cards) == 1:
        return cards[0]
    message = json.dumps([{"id": c.id, "policies": c.policies} for c in cards])
    response = gpt4(message, best_values_card_prompt, function=best_function)
    assert isinstance(response, dict)
    best_values_card_id = response["best_values_card_id"]
    return next((c for c in cards if c.id == best_values_card_id))


def _create_deduplicated_card(card: ValuesCard, deduplication_id: int):
    embeddings = _embed_card(card)
    canonical = db.deduplicatedcard.create(
        data={
            "title": card.title,
            "policies": card.policies,
            "deduplicationId": deduplication_id,
        }
    )
    _link_to_deduplicated_card(card.id, canonical.id, deduplication_id)
    query = f"""UPDATE "DeduplicatedCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {canonical.id};"""
    db.execute_raw(query)
    return canonical


def _link_to_deduplicated_card(
    values_card_id: int, deduplicated_card_id: int, deduplication_id: int
):
    db.valuescardtodeduplicatedcard.create(
        data={
            "deduplicationId": deduplication_id,
            "deduplicatedCardId": deduplicated_card_id,
            "valuesCardId": values_card_id,
        },
    )

    print(
        "Linked card ",
        values_card_id,
        "to deduplicated card ",
        deduplicated_card_id,
        "for deduplication ",
        deduplication_id,
    )


def embed():
    """Embed all ValuesCards."""
    if not db.is_connected():
        db.connect()
    query = f"""SELECT "id", "title", "policies", "generationId", "createdAt", "updatedAt" FROM "ValuesCard" WHERE "embedding" IS NULL;"""
    cards = db.query_raw(query, model=ValuesCard)
    for card in tqdm(cards):
        embeddings = _embed_card(card)
        query = f"""UPDATE "ValuesCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {card.id};"""
        db.execute_raw(query)
    db.disconnect()


def seed():
    """Seed a new deduplication."""
    if not db.is_connected():
        db.connect()
    deduplication = db.deduplication.create(data={"gitCommitHash": "TODO"})  # TODO
    query = f"""SELECT id, embedding::real[] FROM "ValuesCard" WHERE embedding IS NOT NULL;"""
    cards = db.query_raw(query, model=ClusterableObject)
    print(len(cards))
    clusters = [[c.id for c in cluster] for cluster in _cluster(cards)]
    print(f"Found {len(clusters)} clusters.")

    for i, c in tqdm(
        enumerate(clusters)
    ):  # TODO: sanity check that this is the right approach.
        if len(c) < 2:
            print(f"Skipping cluster {i} with only {len(c)} cards...")
        else:
            representative = _get_representative(c)
            canonical = _create_deduplicated_card(representative, deduplication.id)
            for card_id in [id for id in c if id != representative.id]:
                _link_to_deduplicated_card(card_id, canonical.id, deduplication.id)

    print("Created and seeded a new deduplication run: ", deduplication.id)
    return deduplication


def deduplicate() -> None:
    """Deduplicate all non-deduplicated cards for the latest deduplication generation."""
    embed()  # embed all cards.

    db.connect()
    deduplication = db.deduplication.find_first(
        where={"state": ProcessState.IN_PROGRESS}, order={"createdAt": "desc"}
    )

    if deduplication:
        print("Continuing deduplication ", deduplication.id)
    else:
        print("Creating a new deduplication...")
        deduplication = seed()

    # Get all cards that have not been deduplicated yet, in batches of 100.
    offset = 0
    cards: List[ValuesCard] = []
    while True:
        batch = db.valuescard.find_many(
            where={
                "ValuesCardToDeduplicatedCard": {
                    "none": {"deduplicationId": deduplication.id}
                },
            },
            skip=offset,
            take=100,
        )
        if not batch:
            break
        offset += 100
        cards.extend(batch)

    # Deduplicate the cards
    for card in tqdm(cards):
        existing_duplicate = _fetch_similar_deduplicated_card(card, deduplication.id)
        if existing_duplicate:
            _link_to_deduplicated_card(card.id, existing_duplicate.id, deduplication.id)
        else:
            _create_deduplicated_card(card, deduplication.id)
    print(f"Deduplicated {len(cards)} cards for deduplication {deduplication.id}.")

    db.deduplication.update(
        where={"id": deduplication.id}, data={"state": ProcessState.FINISHED}
    )
    db.disconnect()


def main():
    deduplicate()


if __name__ == "__main__":
    main()
