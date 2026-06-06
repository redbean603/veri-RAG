from pathlib import Path
from typing import Any

import chromadb

from config import CHROMA_HOST, CHROMA_PORT, IMAGE_COLLECTION, TEXT_COLLECTION
from embeddings import get_text_embedding


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
    candidate_news_ids: list[str] | None = None,
    query_vector: list[float] | None = None,
) -> list[dict[str, Any]]:
    if candidate_news_ids is not None and not candidate_news_ids:
        return []

    query_embedding = _query_embedding(query=query, query_vector=query_vector)
    query_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if candidate_news_ids is not None:
        query_kwargs["where"] = {"news_id": {"$in": candidate_news_ids}}

    results = get_text_collection().query(
        **query_kwargs,
    )
    return _format_results(results, score_threshold=score_threshold)


def evidence_search(
    query: str,
    query_vector: list[float] | None = None,
    candidate_news_ids: list[str] | None = None,
    candidate_k: int = 50,
    final_k: int = 5,
    use_reranker: bool = True,
) -> list[dict[str, Any]]:
    from hybrid_search import retrieve_and_rerank

    return retrieve_and_rerank(
        query=query,
        query_vector=query_vector,
        candidate_news_ids=candidate_news_ids,
        candidate_k=candidate_k,
        final_k=final_k,
        use_reranker=use_reranker,
    )


def agent_evidence_search(
    query: str,
    candidate_news_ids: list[str],
    json_files: list[str | Path] | None = None,
    json_records: list[dict[str, Any]] | None = None,
    query_vector: list[float] | None = None,
    candidate_k: int = 50,
    final_k: int = 5,
    use_reranker: bool = True,
    persist_json: bool = True,
) -> dict[str, Any]:
    ingest_stats = {
        "loaded": 0,
        "load_failed": 0,
        "upserted": 0,
        "image_upserted": 0,
        "skipped_empty": 0,
        "skipped_image_vector": 0,
        "failed": 0,
    }

    if json_files:
        from ingest import ingest_text_json_files

        ingest_stats = _merge_stats(
            ingest_stats,
            ingest_text_json_files(json_files, persist_json=persist_json),
        )

    if json_records:
        from ingest import ingest_text_records

        ingest_stats = _merge_stats(
            ingest_stats,
            ingest_text_records(json_records, persist_json=persist_json),
        )

    results = evidence_search(
        query=query,
        query_vector=query_vector,
        candidate_news_ids=candidate_news_ids,
        candidate_k=candidate_k,
        final_k=final_k,
        use_reranker=use_reranker,
    )

    formatted_results = [_agent_result(result) for result in results]
    return {
        "selected_news_ids": [result["news_id"] for result in formatted_results],
        "results": formatted_results,
        "ingest": ingest_stats,
    }


def _format_results(
    results: dict[str, Any],
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    formatted = []
    for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        score = 1 - distance
        if score_threshold is not None and score < score_threshold:
            continue

        formatted.append(
            {
                "news_id": metadata.get("news_id") or doc_id,
                "title": metadata.get("title") or metadata.get("summary") or document,
                "url": metadata.get("url", ""),
                "published_at": metadata.get("published_at", ""),
                "source": metadata.get("source", ""),
                "image_path": metadata.get("image_path", ""),
                "content": document,
                "summary": metadata.get("summary", ""),
                "score": score,
                "distance": distance,
            }
        )
    return formatted


def _query_embedding(query: str, query_vector: list[float] | None = None) -> list[float]:
    if query_vector is None:
        return get_text_embedding(query)
    if not isinstance(query_vector, list) or not all(
        isinstance(value, int | float) for value in query_vector
    ):
        raise ValueError("query_vector must be a list of numbers")
    return [float(value) for value in query_vector]


def _agent_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "news_id": result.get("news_id", ""),
        "summary": result.get("summary") or result.get("content", ""),
        "content": result.get("content", ""),
        "similarity_score": result.get("score"),
        "distance": result.get("distance"),
        "fusion_score": result.get("fusion_score"),
        "rerank_score": result.get("rerank_score"),
        "rank_stage": result.get("rank_stage"),
        "title": result.get("title", ""),
        "url": result.get("url", ""),
        "source": result.get("source", ""),
        "published_at": result.get("published_at", ""),
    }


def _merge_stats(base: dict[str, int], update: dict[str, int]) -> dict[str, int]:
    merged = dict(base)
    for key, value in update.items():
        merged[key] = merged.get(key, 0) + int(value)
    return merged
