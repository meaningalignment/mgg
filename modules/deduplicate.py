import argparse
from collections import Counter
from typing import List
from openai import OpenAI
from pydantic import BaseModel
import json
from prisma import Json, Prisma
from prisma.models import DeduplicatedCard, ValuesCard
from prisma.enums import ProcessState
from tqdm import tqdm
from embed import embed_card
from llms import gpt4, sonnet

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


dedupe_cards_prompt = f"""You are given a values card and a list of other canonical values cards. Determine if the value in the input values card is already represented by one of the canonical values. If so, return the id of the canonical values card that represents the source of meaning.

A values card is made up of a set of attentional policies.

{attentional_policy_definition}

# Attentional Policy Guidelines
{attentional_policy_guidelines}

# Guidelines
Two or more values cards are about the same value if:
- A user that articulated one of the cards would feel like the other cards in the cluster capture what they cared about *fully*.
- Someone instructed to pay attention to one set of attention policies would in practice pay attention to the same things as someone instructed to pay attention to the other set.
- Someone asked to design an experience that seeks to enable the attention policies in one card would end up with something that is also serving the attention policies of the other card.
- Any difference in attention policies between the cards would be acknowledged as an oversight or a mistake, and both cards should be updated to reflect the same attention policies.
- The cards are formulated using roughly the same level of granularity and detail.

*Only if the cards pass all of these criteria can they be considered to be about the same value.*"""

dedupe_contexts_prompt = """You will be given a long list of terms.

Your task is to group terms that are synonyms of each other together. Terms (X and Y, for example) can be said to be synonyms if choosing an X is equivalent to choosing a Y.

Return a list of synonym groups, where each term in the group is a synonym of every other term in the group. Each group should be separated by two newlines, and each term in the group should be on its own line. Each group should include as many terms as possible. Ignore all terms in the list that has no exact synonyms. Make sure to exhaust the ENTIRE list. Do not include anything else in your response apart from the terms (each term should be on its own line), and the newlines separating the synonym groups. Do not format your response in any other way. DO NOT repeat terms in your response."""

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


def _fetch_duplicate_card(
    candidate: ValuesCard, cards: List[ValuesCard]
) -> ValuesCard | None:
    user_prompt = json.dumps(
        {
            "input_values_card": {"policies": candidate.policies},
            "canonical_values_cards": [
                {"id": c.id, "policies": c.policies} for c in cards
            ],
        }
    )
    try:
        response = gpt4(
            user_prompt,
            dedupe_cards_prompt,
            function=dedupe_function,
            token_counter=counter,
        )
        assert isinstance(response, dict)
        matching_id = response["canonical_card_id"]
        return next((c for c in cards if c.id == matching_id), None)
    except Exception as e:
        print("Error fetching duplicate card: ", e)
        return None


def _create_deduplicated_card(card: ValuesCard, deduplication_id: int):
    canonical = db.deduplicatedcard.create(
        data={
            "title": card.title,
            "policies": card.policies,
            "deduplicationId": deduplication_id,
        }
    )
    _link_to_deduplicated_card(card.id, canonical.id, deduplication_id)
    return canonical


def _merge_deduplicate_cards(db_duplicate_1, db_duplicate_2, deduplication_id):
    print(f"Merging deduplicated cards {db_duplicate_1.id} and {db_duplicate_2.id}...")

    try:
        # Find all ValuesCards linked to db_duplicate_1
        linked_cards = db.valuescardtodeduplicatedcard.find_many(
            where={"deduplicatedCardId": db_duplicate_1.id}
        )

        # Relink all these cards to db_duplicate_2
        for link in linked_cards:
            db.valuescardtodeduplicatedcard.upsert(
                where={
                    "valuesCardId_deduplicatedCardId_deduplicationId": {
                        "valuesCardId": link.valuesCardId,
                        "deduplicatedCardId": db_duplicate_2.id,
                        "deduplicationId": deduplication_id,
                    }
                },
                data={
                    "create": {
                        "valuesCardId": link.valuesCardId,
                        "deduplicatedCardId": db_duplicate_2.id,
                        "deduplicationId": deduplication_id,
                    },
                    "update": {},
                },
            )

        # Now that all cards are relinked, we can safely delete db_duplicate_1
        db.deduplicatedcard.delete(where={"id": db_duplicate_1.id})

        print(
            f"Successfully merged deduplicated card {db_duplicate_1.id} into {db_duplicate_2.id}"
        )
    except Exception as e:
        print(f"Error during merge: {str(e)}")
        # You might want to add some error handling or logging here
        raise  # Re-raise the exception to be handled by the caller if necessary


def _link_to_deduplicated_card(
    values_card_id: int, deduplicated_card_id: int, deduplication_id: int
):
    db.valuescardtodeduplicatedcard.upsert(
        where={
            "valuesCardId_deduplicatedCardId_deduplicationId": {
                "valuesCardId": values_card_id,
                "deduplicatedCardId": deduplicated_card_id,
                "deduplicationId": deduplication_id,
            }
        },
        data={
            "create": {
                "valuesCardId": values_card_id,
                "deduplicatedCardId": deduplicated_card_id,
                "deduplicationId": deduplication_id,
            },
            "update": {},
        },
    )

    print(
        f"Linked card {values_card_id} to deduplicated card {deduplicated_card_id} for deduplication {deduplication_id}"
    )


def _get_or_create_deduplication():
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
    deduplication = db.deduplication.create(data={"gitCommitHash": "TODO"})
    db.disconnect()
    return deduplication


def _deduplicate_cards_for_contexts(
    deduplication_id: int, generation_id: int, contexts: List[str]
) -> None:
    """Deduplicate cards for a set of contexts for the latest deduplication generation."""
    if not db.is_connected():
        db.connect()

    # Get all cards that have not been deduplicated yet that is either linked to or from one of the contexts.
    cards = db.valuescard.find_many(
        where={
            "generationId": generation_id,
            "ValuesCardToDeduplicatedCard": {
                "none": {"deduplicationId": deduplication_id}
            },
            "OR": [
                {"From": {"some": {"contextName": {"in": contexts}}}},
                {"To": {"some": {"contextName": {"in": contexts}}}},
            ],
        },
    )

    print(
        f"Deduplicating {len(cards)} cards for {len(contexts)} contexts ({', '.join(contexts)})..."
    )

    # Deduplicate the cards
    for card_1 in cards:
        # Check wether the first card is already deduplicated.
        db_duplicate_1 = db.deduplicatedcard.find_first(
            where={
                "ValuesCardToDeduplicatedCard": {"some": {"valuesCardId": card_1.id}},
                "deduplicationId": deduplication_id,
            }
        )

        # Use a prompt to see if any other card in the cluster is a duplicate of this card.
        other_cards = [c for c in cards if c.id != card_1.id]
        card_2 = _fetch_duplicate_card(card_1, other_cards)
        if not card_2:
            print(
                f"No duplicate found in cluster for card {card_1.id}. Deduplicating it..."
            )
            if not db_duplicate_1:
                _create_deduplicated_card(card_1, deduplication_id)
            continue

        print("Found duplicate  card", card_2.id)

        # Check wether the second card is already deduplicated.
        db_duplicate_2 = db.deduplicatedcard.find_first(
            where={
                "ValuesCardToDeduplicatedCard": {"some": {"valuesCardId": card_2.id}},
                "deduplicationId": deduplication_id,
            }
        )

        # If both cards are already deduplicated into the same card, continue.
        if db_duplicate_1 and db_duplicate_2 and db_duplicate_1.id == db_duplicate_2.id:
            continue
        # If both cards have been independently deduplicated into different cards, merge them.
        if db_duplicate_1 and db_duplicate_2:
            _merge_deduplicate_cards(db_duplicate_1, db_duplicate_2, deduplication_id)
        # If the first card is already deduplicated, link the second to it...
        elif db_duplicate_1:
            _link_to_deduplicated_card(card_2.id, db_duplicate_1.id, deduplication_id)
        # ...or vice versa.
        elif db_duplicate_2:
            _link_to_deduplicated_card(card_1.id, db_duplicate_2.id, deduplication_id)
        # If no cards are deduplicated, create a new deduplicated card for the first card,
        # and link the second to it.
        else:
            db_duplicate_2 = _create_deduplicated_card(card_2, deduplication_id)
            _link_to_deduplicated_card(card_1.id, db_duplicate_2.id, deduplication_id)

    print(f"Deduplicated {len(cards)} cards for deduplication {deduplication_id}.")

    db.disconnect()


def _deduplicate_contexts(deduplication_id: int, generation_id: int):
    """Deduplicate all contexts."""
    if not db.is_connected():
        db.connect()

    # Find all contexts.
    contexts = [
        e.contextName
        for e in db.edge.find_many(
            where={
                "generationId": generation_id,
                "EdgeToDeduplicatedEdge": {
                    "none": {"DeduplicatedEdge": {"deduplicationId": deduplication_id}}
                },
            }
        )
    ]
    contexts = sorted(list(set(contexts)))
    print(f"Deduplicating {len(contexts)} unique contexts...")

    response = sonnet(
        "\n".join(contexts),
        dedupe_contexts_prompt,
        temperature=0.0,
        max_tokens=8192,
    )
    clusters = response.strip().split("\n\n")
    clusters = [c.split("\n") for c in clusters]

    # convert list of list to dict, where the key is last element of each list.
    clusters = {c[-1]: c[:-1] for c in clusters}

    print(f"Found {len(clusters)} clusters of duplicate contexts:")
    print(clusters)

    # Include all the contexts that were not deduplicated.
    for context in contexts:
        if context in clusters.keys():
            continue
        if context in [c for v in clusters.values() for c in v]:
            continue
        clusters[context] = [context]

    # Add all clusters to the database for the deduplication.
    db.deduplicatedcontext.create_many(
        data=[
            {"name": context, "deduplicationId": deduplication_id}
            for context in clusters.keys()
        ],
        skip_duplicates=True,
    )

    # Create a mapping from any context to the corresponding db context.
    mapping = {v: k for k, v_list in clusters.items() for v in v_list}
    mapping.update({k: k for k in clusters.keys()})

    return clusters, mapping


def _deduplicate_edges(
    deduplication_id: int, generation_id: int, context_mapping: dict
) -> None:
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

    # Deduplicate all edges.
    for edge in tqdm(edges, desc="Deduplicating edges"):
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
        #
        # Allow self-edges for now (to surface them when fetching winning values).
        #
        # if from_deduplicated_card.id == to_deduplicated_card.id:
        #     print(
        #         f"Two cards in an edge are the same deduplicated card: {from_deduplicated_card.id}"
        #     )
        #     continue
        print("Deduplicating edge from", edge.fromId, "to", edge.toId)
        # Reconstruct the edge between the two deduplicated cards.
        db.deduplicatededge.upsert(
            where={
                "fromId_toId_contextName": {
                    "fromId": from_deduplicated_card.id,
                    "toId": to_deduplicated_card.id,
                    "contextName": context_mapping[edge.contextName],
                }
            },
            data={
                "create": {
                    "fromId": from_deduplicated_card.id,
                    "toId": to_deduplicated_card.id,
                    "metadata": Json(edge.metadata),
                    "contextName": context_mapping[edge.contextName],
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
                "deduplicatedContextName": context_mapping[edge.contextName],
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
                context_mapping[c] for c in original_ctx if c in context_mapping
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

    # Create or continue deduplication run.
    deduplication = _get_or_create_deduplication()

    # Deduplicate contexts.
    clusters, mapping = _deduplicate_contexts(deduplication.id, generation_id)

    for context, context_dupes in tqdm(clusters.items(), desc="Deduplicating contexts"):
        _deduplicate_cards_for_contexts(
            deduplication.id, generation_id, [context, *context_dupes]
        )

    # Deduplicate edges.
    _deduplicate_edges(deduplication.id, generation_id, mapping)

    # Mark the deduplication as finished.
    _finish_deduplication(deduplication.id)
    print(f"Finished deduplication {deduplication.id}.")
    print(
        "price: ",
        gp4o_price(token_counter),
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
