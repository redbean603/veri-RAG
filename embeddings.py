import os

from dotenv import load_dotenv
from openai import OpenAI

from config import TEXT_EMBEDDING_MODEL


load_dotenv()

_openai_client: OpenAI | None = None


def get_text_embedding(text: str) -> list[float]:
    client = _get_openai_client()
    response = client.embeddings.create(
        model=TEXT_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client
