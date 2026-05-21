from pathlib import Path
from typing import Any

import chromadb

from config import CHROMA_HOST, CHROMA_PORT, IMAGE_COLLECTION, TEXT_COLLECTION
from embeddings import get_image_embedding, get_text_embedding


_chroma_client: chromadb.HttpClient | None = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return _chroma_client


def get_text_collection():
    return get_chroma_client().get_or_create_collection(
        name=TEXT_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def get_image_collection():
    return get_chroma_client().get_or_create_collection(
        name=IMAGE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def vector_search(
    query: str,
    top_k: int = 3,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    query_embedding = get_text_embedding(query)
    results = get_text_collection().query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return _format_results(results, score_threshold=score_threshold)


def image_search(
    image_path: str | Path,
    top_k: int = 3,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    query_embedding = get_image_embedding(image_path)
    results = get_image_collection().query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return _format_results(results, score_threshold=score_threshold)


def _format_results(
    results: dict[str, Any],
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    formatted = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        score = 1 - distance
        if score_threshold is not None and score < score_threshold:
            continue

        formatted.append(
            {
                "title": metadata.get("title") or document,
                "url": metadata.get("url", ""),
                "published_at": metadata.get("published_at", ""),
                "source": metadata.get("source", ""),
                "image_path": metadata.get("image_path", ""),
                "content": document,
                "score": score,
                "distance": distance,
            }
        )
    return formatted
