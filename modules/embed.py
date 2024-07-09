import json
from typing import List
from openai import OpenAI

from prisma import Prisma
from tqdm import tqdm
from prisma.models import DeduplicatedCard, ValuesCard

db = Prisma()
client = OpenAI()


def embed_card(card: ValuesCard | DeduplicatedCard) -> List[float]:
    text = (
        "It feels meaningful to pay attention to the following in certain choices for me:\n"
        + "\n".join(card.policies)
    )
    response = client.embeddings.create(
        model="text-embedding-3-large", input=text, dimensions=1536
    )
    return response.data[0].embedding


def embed_cards(generation_id: int):
    """Embed all ValuesCards for a generation."""

    if not db.is_connected():
        db.connect()

    query = f"""SELECT "id", "title", "policies", "generationId", "createdAt", "updatedAt" FROM "ValuesCard" WHERE "embedding" IS NULL AND "generationId" = {generation_id};"""
    cards = db.query_raw(query, model=ValuesCard)

    print("Embedding all values cards...")

    for card in tqdm(cards):
        embeddings = embed_card(card)
        query = f"""UPDATE "ValuesCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {card.id};"""
        db.execute_raw(query)
    db.disconnect()


def embed_all_cards():
    """Embed all ValuesCards."""

    if not db.is_connected():
        db.connect()

    query = f"""SELECT "id", "title", "policies", "generationId", "createdAt", "updatedAt" FROM "ValuesCard" WHERE "embedding" IS NULL;"""
    cards = db.query_raw(query, model=ValuesCard)

    print("Embedding all values cards...")

    for card in tqdm(cards):
        embeddings = embed_card(card)
        query = f"""UPDATE "ValuesCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {card.id};"""
        db.execute_raw(query)
    db.disconnect()


if __name__ == "__main__":
    """Embed all cards."""
    embed_all_cards()
