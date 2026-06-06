from __future__ import annotations

import json
import re
from typing import Any

from config import JSON_FOLDER
from reranker import LocalReranker
from search import vector_search


def retrieve_and_rerank(
    query: str,
    query_vector: list[float] | None = None,
    candidate_news_ids: list[str] | None = None,
    candidate_k: int = 50,
    final_k: int = 5,
    score_threshold: float | None = None,
    use_reranker: bool = True,
) -> list[dict[str, Any]]:
    candidate_news_ids = _normalize_candidate_ids(candidate_news_ids)
    if candidate_news_ids is not None and not candidate_news_ids:
        return []

    vector_results = vector_search(
        query=query,
        top_k=candidate_k,
        score_threshold=score_threshold,
        candidate_news_ids=candidate_news_ids,
        query_vector=query_vector,
    )
    keyword_results = keyword_search(
        query,
        top_k=candidate_k,
        candidate_news_ids=candidate_news_ids,
    )
    candidates = fuse_candidates(vector_results, keyword_results)

    if not candidates:
        return []

    if not use_reranker:
        return _vector_fallback(candidates, top_k=final_k)

    reranker = LocalReranker()
    return reranker.rerank(query=query, documents=candidates, top_k=final_k)


def keyword_search(
    query: str,
    top_k: int = 50,
    candidate_news_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    allowed_ids = set(candidate_news_ids) if candidate_news_ids is not None else None
    scored = []
    for data in _iter_news_records():
        news_id = str(data.get("news_id") or "")
        if not news_id:
            continue
        if allowed_ids is not None and news_id not in allowed_ids:
            continue

        title = str(data.get("title") or "")
        content = _record_text(data)
        title_terms = _tokenize(title)
        content_terms = _tokenize(content)
        score = _keyword_score(query_terms, title_terms, content_terms)
        if score <= 0:
            continue

        scored.append(
            {
                "news_id": news_id,
                "title": _display_title(data),
                "url": data.get("url", ""),
                "published_at": data.get("published_at", ""),
                "source": data.get("source", ""),
                "image_path": "",
                "content": content,
                "summary": data.get("summary", ""),
                "score": score,
                "distance": None,
                "rank_stage": "keyword",
            }
        )

    scored.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return scored[:top_k]


def fuse_candidates(
    vector_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    method: str = "rrf",
) -> list[dict[str, Any]]:
    if not keyword_results:
        return vector_results

    merged: dict[str, dict[str, Any]] = {}
    for rank, result in enumerate(vector_results, start=1):
        key = _candidate_key(result)
        item = dict(result)
        item["fusion_score"] = _rrf_score(rank)
        merged[key] = item

    for rank, result in enumerate(keyword_results, start=1):
        key = _candidate_key(result)
        score = _rrf_score(rank)
        if key in merged:
            merged[key]["fusion_score"] = merged[key].get("fusion_score", 0.0) + score
        else:
            item = dict(result)
            item["fusion_score"] = score
            merged[key] = item

    return sorted(
        merged.values(),
        key=lambda item: (item.get("fusion_score", 0.0), item.get("score", 0.0)),
        reverse=True,
    )


def _vector_fallback(
    documents: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    results = []
    for document in documents:
        item = dict(document)
        item["rerank_score"] = float(item.get("score", 0.0) or 0.0)
        item["rank_stage"] = "vector_fallback"
        results.append(item)

    results.sort(
        key=lambda item: (
            item.get("fusion_score", 0.0),
            item.get("score", 0.0),
        ),
        reverse=True,
    )
    return results[:top_k]


def _candidate_key(result: dict[str, Any]) -> str:
    return str(result.get("news_id") or result.get("url") or result.get("title") or id(result))


def _rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def _normalize_candidate_ids(candidate_news_ids: list[str] | None) -> list[str] | None:
    if candidate_news_ids is None:
        return None
    return [str(news_id) for news_id in dict.fromkeys(candidate_news_ids) if str(news_id)]


def _iter_news_records():
    for json_path in sorted(JSON_FOLDER.glob("*_result.json")):
        try:
            with json_path.open("r", encoding="utf-8") as file:
                yield json.load(file)
        except (OSError, json.JSONDecodeError):
            continue


def _display_title(data: dict[str, Any]) -> str:
    return str(data.get("title") or data.get("summary") or "")


def _record_text(data: dict[str, Any]) -> str:
    summary = str(data.get("summary") or "").strip()
    if summary:
        return summary

    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    return "\n".join(part for part in (title, content) if part)


def _keyword_score(
    query_terms: list[str],
    title_terms: list[str],
    content_terms: list[str],
) -> float:
    title_counts = _term_counts(title_terms)
    content_counts = _term_counts(content_terms)
    score = 0.0

    for term in query_terms:
        if term in title_counts:
            score += 2.0 * title_counts[term]
        if term in content_counts:
            score += content_counts[term]

    return score / max(1, len(query_terms))


def _term_counts(terms: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for term in terms:
        counts[term] = counts.get(term, 0) + 1
    return counts


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[0-9A-Za-z_\uac00-\ud7a3]+", text)
        if len(token) > 1
    ]
