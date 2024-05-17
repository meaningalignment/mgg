import argparse
from collections import Counter
from typing import List
from openai import OpenAI
from pydantic import BaseModel
from sklearn.cluster import DBSCAN
import numpy as np
import json
from prisma import Json, Prisma
from prisma.models import DeduplicatedCard, ValuesCard
from prisma.enums import ProcessState
from tqdm import tqdm
from embed import embed_card, embed_cards
from gpt import gpt4
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

from prompt_segments import attentional_policy_definition, attentional_policy_guidelines

from utils import *

counter = Counter()


class ClusterableObject(BaseModel):
    id: int
    embedding: List[float]


class CardWithDistance(DeduplicatedCard):
    distance: float


db = Prisma()
client = OpenAI()


dedupe_prompt = f"""
You are given a values card and a list of other canonical values cards. Determine if the value in the input values card is already represented by one of the canonical values. If so, return the id of the canonical values card that represents the source of meaning.

# Guidelines
Two or more values cards are about the same value if:
- A user that articulated one of the cards would feel like the other cards in the cluster capture what they cared about *fully*.
- Someone instructed to pay attention to one set of attention policies would pay attention to exactly the same things as someone instructed to pay attention to the other set.
- Any difference in attention policies between the cards would be acknowledged as an oversight or a mistake, and both cards should be updated to reflect the same attention policies.
- The cards are formulated using roughly the same level of granularity and detail.

Only if the cards pass all of these criteria can they be considered to be about the same value.
"""

best_values_card_prompt = f"""
You will be provided with a list of "values cards", all representing the same value. Your task is to return the "id" of the "values card" which has the best attentional policies, according to the guidelines below.

{attentional_policy_definition}

{attentional_policy_guidelines}
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


def _cluster(
    objects: List[ClusterableObject], eps: float = 0.05, min_samples: int = 3
) -> List[List[ClusterableObject]]:
    embeddings = np.array([obj.embedding for obj in objects])
    distance_matrix = cosine_distances(embeddings)

    # Run DBSCAN
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed").fit(
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


@retry(times=3)
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
    response = gpt4(
        user_prompt, dedupe_prompt, function=dedupe_function, token_counter=counter
    )
    assert isinstance(response, dict)
    matching_id = response["canonical_card_id"]
    return next((c for c in similar_cards if c.id == matching_id), None)


@retry(times=3)
def _get_representative(card_ids: List[int]):
    cards = db.valuescard.find_many(where={"id": {"in": card_ids}})
    if len(cards) == 1:
        return cards[0]
    message = json.dumps([{"id": c.id, "policies": c.policies} for c in cards])
    response = gpt4(
        message, best_values_card_prompt, function=best_function, token_counter=counter
    )
    assert isinstance(response, dict)
    best_values_card_id = response["best_values_card_id"]
    return next((c for c in cards if c.id == best_values_card_id))


def _create_deduplicated_card(card: ValuesCard, deduplication_id: int):
    embeddings = embed_card(card)
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


def _get_or_create_deduplication(generation_id: int):
    if not db.is_connected():
        db.connect()
    deduplication = db.deduplication.find_first(
        where={"state": ProcessState.IN_PROGRESS}, order={"createdAt": "desc"}
    )

    if deduplication:
        print("Continuing deduplication ", deduplication.id)
        db.disconnect()
        return deduplication

    print("Creating a new deduplication...")

    deduplication = db.deduplication.create(data={"gitCommitHash": "TODO"})  # TODO

    # Cluster non-deduplicated cards.
    query = f"""SELECT id, embedding::real[] FROM "ValuesCard" WHERE embedding IS NOT NULL AND "generationId" = {generation_id};"""
    cards = db.query_raw(query, model=ClusterableObject)
    if not cards:
        raise ValueError("No cards to deduplicate.")
    clusters = [[c.id for c in cluster] for cluster in _cluster(cards)]
    print(f"Found {len(clusters)} clusters for {len(cards)} cards.")

    # Create a deduplicated card for each cluster.
    for i, c in tqdm(enumerate(clusters)):
        if len(c) < 2:
            print(f"Skipping cluster {i} with only {len(c)} cards...")
        else:
            representative = _get_representative(c)
            canonical = _create_deduplicated_card(representative, deduplication.id)
            for card_id in [id for id in c if id != representative.id]:
                _link_to_deduplicated_card(card_id, canonical.id, deduplication.id)

    db.disconnect()
    return deduplication


def _deduplicate_cards(deduplication_id: int, generation_id: int) -> None:
    """Deduplicate all non-deduplicated cards for the latest deduplication generation."""
    if not db.is_connected():
        db.connect()

    # Get all cards that have not been deduplicated yet.
    cards = db.valuescard.find_many(
        where={
            "generationId": generation_id,
            "ValuesCardToDeduplicatedCard": {
                "none": {"deduplicationId": deduplication_id}
            },
        }
    )

    # Deduplicate the cards
    for card in tqdm(cards):
        existing_duplicate = _fetch_similar_deduplicated_card(card, deduplication_id)
        if existing_duplicate:
            _link_to_deduplicated_card(card.id, existing_duplicate.id, deduplication_id)
        else:
            _create_deduplicated_card(card, deduplication_id)
    print(f"Deduplicated {len(cards)} cards for deduplication {deduplication_id}.")

    db.disconnect()


def _ctx_cluster_repr(contexts: List[str]) -> str:
    return contexts[0].title()


def _deduplicate_contexts(
    deduplication_id: int, contexts: List[str]
) -> List[List[str]]:
    """Deduplicate all contexts."""
    embeddings = client.embeddings.create(
        model="text-embedding-3-large", input=[c.lower() for c in contexts]
    )
    cluster_objs = [
        ClusterableObject(id=i, embedding=embeddings.data[i].embedding)
        for i in range(len(contexts))
    ]
    clusters = [
        [contexts[c.id] for c in cluster]
        for cluster in _cluster(cluster_objs, eps=0.25, min_samples=1)
    ]
    print(f"Turned {len(contexts)} contexts into {len(clusters)} clusters.")

    # Add all deduplicated contexts to the database for the deduplication.
    for cluster in clusters:
        # For now, just use the first context as the representative.
        context = _ctx_cluster_repr(cluster)
        db.deduplicatedcontext.upsert(
            where={
                "name_deduplicationId": {
                    "name": context,
                    "deduplicationId": deduplication_id,
                }
            },
            data={
                "create": {"name": context, "deduplicationId": deduplication_id},
                "update": {},
            },
        )

    return clusters


def _deduplicate_edges_and_contexts(deduplication_id: int, generation_id: int) -> None:
    """Deduplicate all edges for the latest deduplication generation."""
    if not db.is_connected():
        db.connect()

    # Find all edges that are not deduplicated yet.
    edges = db.edge.find_many(
        where={
            "generationId": generation_id,
            "EdgeToDeduplicatedEdge": {
                "none": {"DeduplicatedEdge": {"deduplicationId": deduplication_id}}
            },
        }
    )

    # Deduplicate contexts.
    contexts = list([e.contextName for e in edges])
    deduplicated_contexts = _deduplicate_contexts(deduplication_id, contexts)
    # Create lookup table.
    ctx_to_deduped_ctx = {
        ctx: _ctx_cluster_repr(cluster)
        for cluster in deduplicated_contexts
        for ctx in cluster
    }

    # Deduplicate all edges.
    for edge in tqdm(edges):
        # Find the deduplicated cards for the edge.
        from_deduplicated_card = db.deduplicatedcard.find_first(
            where={
                "ValuesCardToDeduplicatedCard": {"some": {"valuesCardId": edge.fromId}},
                "deduplicationId": deduplication_id,
            }
        )
        to_deduplicated_card = db.deduplicatedcard.find_first(
            where={
                "ValuesCardToDeduplicatedCard": {"some": {"valuesCardId": edge.toId}},
                "deduplicationId": deduplication_id,
            }
        )
        if not from_deduplicated_card or not to_deduplicated_card:
            print(
                f"Could not find deduplicated cards for values cards {edge.fromId} and {edge.toId}"
            )
            continue
        if from_deduplicated_card.id == to_deduplicated_card.id:
            print(
                f"Two cards in an edge are the same deduplicated card: {from_deduplicated_card.id}"
            )
            continue
        print("Deduplicating edge from", edge.fromId, "to", edge.toId)
        # Reconstruct the edge between the two deduplicated cards.
        db.deduplicatededge.upsert(
            where={
                "fromId_toId_contextName": {
                    "fromId": from_deduplicated_card.id,
                    "toId": to_deduplicated_card.id,
                    "contextName": ctx_to_deduped_ctx[edge.contextName],
                }
            },
            data={
                "create": {
                    "fromId": from_deduplicated_card.id,
                    "toId": to_deduplicated_card.id,
                    "metadata": Json(edge.metadata),
                    "contextName": ctx_to_deduped_ctx[edge.contextName],
                    "deduplicationId": deduplication_id,
                },
                "update": {},
            },
        )
        # Link the deduplicated edge to the deduplicated context.
        db.edgetodeduplicatededge.create(
            data={
                "fromId": edge.fromId,
                "toId": edge.toId,
                "contextName": edge.contextName,
                "deduplicatedFromId": from_deduplicated_card.id,
                "deduplicatedToId": to_deduplicated_card.id,
                "deduplicatedContextName": ctx_to_deduped_ctx[edge.contextName],
            }
        )
        # Link deduplicated contexts to deduplicated cards directly.
        for card in [from_deduplicated_card, to_deduplicated_card]:
            original_cards = db.valuescard.find_many(
                where={
                    "ValuesCardToDeduplicatedCard": {
                        "some": {"deduplicatedCardId": card.id}
                    }
                }
            )
            original_ctx = [c.choiceContext for c in original_cards]
            deduped_ctx = [
                ctx_to_deduped_ctx[c] for c in original_ctx if c in ctx_to_deduped_ctx
            ]

            # Link the deduplicated card to the deduplicated contexts.
            for dc in deduped_ctx:
                db.deduplicatedcardtocontext.upsert(
                    where={
                        "deduplicatedCardId_deduplicatedContextId_deduplicationId": {
                            "deduplicatedCardId": card.id,
                            "deduplicatedContextId": dc,
                            "deduplicationId": deduplication_id,
                        }
                    },
                    data={
                        "create": {
                            "deduplicatedCardId": card.id,
                            "deduplicatedContextId": dc,
                            "deduplicationId": deduplication_id,
                        },
                        "update": {},
                    },
                )
    db.disconnect()


def _finish_deduplication(deduplication_id: int):
    db.connect()
    db.deduplication.update(
        where={"id": deduplication_id}, data={"state": ProcessState.FINISHED}
    )
    db.disconnect()


def deduplicate(generation_id: int | None = None):
    token_counter = Counter()
    # If no generation_id is provided, use the latest generation.
    if generation_id is None:
        db.connect()
        gen = db.generation.find_first(order={"createdAt": "desc"})
        if not gen:
            raise ValueError("No generation found.")
        generation_id = gen.id
        db.disconnect()
        print(f"Deduplicating generation {generation_id}")

    embed_cards(generation_id)
    # Create or continue deduplication run.
    deduplication = _get_or_create_deduplication(generation_id)
    # Deduplicate cards, edges and contexts.
    _deduplicate_cards(deduplication.id, generation_id)
    _deduplicate_edges_and_contexts(deduplication.id, generation_id)
    # Mark the deduplication as finished.
    _finish_deduplication(deduplication.id)
    print(f"Finished deduplication {deduplication.id}.")
    print(
        "price: ",
        calculate_gp4o_price(
            token_counter["prompt_tokens"], token_counter["completion_tokens"]
        ),
    )


if __name__ == "__main__":
    """Deduplicate a generation."""
    parser = argparse.ArgumentParser(description="Deduplicate a graph.")
    parser.add_argument(
        "--generation_id",
        type=int,
        help="The generation to deduplicate.",
    )
    args = parser.parse_args()
    deduplicate(args.generation_id)
