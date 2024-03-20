from typing import List
from openai import OpenAI
from pydantic import BaseModel
from sklearn.cluster import DBSCAN
import numpy as np
import json
from prisma import Prisma
from prisma.models import DeduplicatedCard, ValuesCard
from tqdm import tqdm
from gpt import gpt4

from prompt_segments import attentional_policy_definition


class ClusterableObject(BaseModel):
    id: int
    embedding: List[float]


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


def __embed_card(card: ValuesCard | DeduplicatedCard) -> List[float]:
    text = "\n".join(card.policies)  # TODO - include something about choice type.
    response = client.embeddings.create(model="text-embedding-3-large", input=text)
    return response.data[0].embedding


def __similarity_search(
    candidate: ValuesCard, deduplication_id: int, limit: int = 5, threshold: float = 0.1
) -> List[DeduplicatedCard]:
    embeddings = __embed_card(candidate)
    query = f'SELECT DISTINCT c.id, c.title, c."policies", c.embedding <=> \'{embeddings}\'::vector as "_distance" FROM "DeduplicatedCard" c WHERE "deduplicationId" = {deduplication_id} ORDER BY "_distance" ASC LIMIT {limit};'
    result = db.query_raw(query, model=DeduplicatedCard)
    return [r for r in result if r.__dict__["_distance"] < threshold]


def __cluster(objects: List[ClusterableObject]):
    scan = DBSCAN(eps=0.11, min_samples=3)  # TODO: actually fix
    return scan.fit(np.asarray(objects)).components_


def __fetch_similar_deduplicated_card(
    candidate: ValuesCard, deduplication_id: int
) -> DeduplicatedCard | None:
    similar_cards = __similarity_search(candidate, deduplication_id)
    if not similar_cards:
        return None
    user_prompt = json.dumps(
        {
            "input_values_card": candidate,
            "canonical_values_cards": [
                {"id": c.id, "policies": c.policies} for c in similar_cards
            ],
        }
    )
    response = gpt4(user_prompt, dedupe_prompt, function=dedupe_function)
    assert isinstance(response, dict)
    matching_id = response["canonical_card_id"]
    return next((c for c in similar_cards if c.id == matching_id), None)


def __get_representative(card_ids: List[int]):
    cards = db.valuescard.find_many(where={"id": {"in": card_ids}})
    if len(cards) == 1:
        return cards[0]
    message = json.dumps([{"id": c.id, "policies": c.policies} for c in cards])
    response = gpt4(message, best_values_card_prompt, function=best_function)
    assert isinstance(response, dict)
    best_values_card_id = response["best_values_card_id"]
    return next((c for c in cards if c.id == best_values_card_id))


def __create_deduplicated_card(card: ValuesCard, deduplication_id: int):
    canonical = db.deduplicatedcard.create(
        data={
            "generation": deduplication_id,
            "title": card.title,
            "policies": card.policies,
            "ValuesCardToDeduplicatedCard": {"create": {"valuesCardId": card.id}},
        },
    )
    embeddings = __embed_card(card)
    query = f"""UPDATE "DeduplicatedCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {canonical.id};"""
    db.execute_raw(query)


def __link_to_deduplicated_card(
    card: ValuesCard, existing_duplicate: DeduplicatedCard, deduplication_id: int
):
    db.valuescardtodeduplicatedcard.create(
        data={
            "deduplicationGenerationId": deduplication_id,
            "deduplicatedCardId": existing_duplicate.id,
            "valuesCardId": card.id,
        }
    )
    print(f"Linked card {card.id} to existing canonical card")


def embed():
    """Embed all ValuesCards."""

    db.connect()
    cards = db.query_raw(
        """SELECT * FROM "ValuesCard" WHERE embedding IS NULL""", model=ValuesCard
    )
    for card in tqdm(cards):
        embeddings = __embed_card(card)
        query = f"""UPDATE "DeduplicatedCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {card.id};"""
        db.execute_raw(query)
    db.disconnect()


def seed():
    """Seed a new deduplication."""

    db.connect()
    deduplication = db.deduplicationgeneration.create(
        data={"gitCommitHash": "TODO"}  # TODO
    )
    cards = db.query_raw(
        'SELECT id, embedding::real[] FROM "ValuesCard"', model=ClusterableObject
    )
    clusters = [c.id for c in __cluster(cards)]  # TODO: right model
    print(f"Found {len(clusters)} clusters.")

    for i, c in tqdm(
        enumerate(clusters)
    ):  # TODO: sanity check that this is the right approach.
        if len(c) < 2:
            print(f"Skipping cluster {i} with only {len(c)} cards...")
        else:
            __create_deduplicated_card(__get_representative(c), deduplication.id)


def deduplicate() -> None:
    """Deduplicate all non-deduplicated cards for the latest deduplication generation."""

    db.connect()
    deduplication = db.deduplicationgeneration.find_first(order={"createdAt": "desc"})
    if not deduplication:
        return print("No seed clusters exist for deduplication. Run `seed()` first.")
    cards = db.valuescard.find_many(
        where={
            "ValuesCardDeduplicatedCard": {"none": {"deduplication": deduplication.id}}
        },
        take=100,
    )
    for card in tqdm(cards):
        existing_duplicate = __fetch_similar_deduplicated_card(card, deduplication.id)
        if existing_duplicate:
            __link_to_deduplicated_card(card, existing_duplicate, deduplication.id)
        else:
            __create_deduplicated_card(card, deduplication.id)
    print(f"Deduplicated {len(cards)} cards for deduplication {deduplication.id}.")
    db.disconnect()
