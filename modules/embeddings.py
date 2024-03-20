import json
from typing import List
import openai
from prisma import Prisma
from prisma.models import ValuesCard, DeduplicatedCard
from tqdm import tqdm

client = openai.OpenAI()
db = Prisma()


def embed_card(card: ValuesCard | DeduplicatedCard) -> List[float]:
    text = "\n".join(card.policies)  # TODO - include something about choice type.
    response = client.embeddings.create(model="text-embedding-3-large", input=text)
    return response.data[0].embedding


def similarity_search(
    candidate: ValuesCard, deduplication_id: int, limit: int = 5, threshold: float = 0.1
) -> List[DeduplicatedCard]:
    embeddings = embed_card(candidate)
    query = f'SELECT DISTINCT c.id, c.title, c."policies", c.embedding <=> \'{embeddings}\'::vector as "_distance" FROM "DeduplicatedCard" c WHERE "deduplicationId" = {deduplication_id} ORDER BY "_distance" ASC LIMIT {limit};'
    result = db.query_raw(query, model=DeduplicatedCard)
    return [r for r in result if r.__dict__["_distance"] < threshold]


def embed():
    db.connect()
    cards = db.query_raw(
        """SELECT * FROM "ValuesCard" WHERE embedding IS NULL""", model=ValuesCard
    )
    for card in tqdm(cards):
        embeddings = embed_card(card)
        query = f"""UPDATE "DeduplicatedCard" SET embedding = '{json.dumps(embeddings)}'::vector WHERE id = {card.id};"""
        db.execute_raw(query)
    db.disconnect()
