from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any


LABELS_PATH = Path("eval/retrieval_labels.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval smoke metrics.")
    parser.add_argument("--mode", choices=["vector", "rerank"], default="rerank")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--labels", type=Path, default=LABELS_PATH)
    args = parser.parse_args()

    labels = load_labels(args.labels)
    if not labels:
        raise SystemExit(f"No labels found at {args.labels}")

    metrics = evaluate(labels=labels, mode=args.mode, k=args.k)
    print(f"Mode: {args.mode}")
    print(f"K: {args.k}")
    print(f"Queries: {metrics['queries']}")
    print(f"Recall@{args.k}: {metrics['recall']:.3f}")
    print(f"MRR@{args.k}: {metrics['mrr']:.3f}")
    print(f"nDCG@{args.k}: {metrics['ndcg']:.3f}")


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            query_id = row["query_id"]
            grouped.setdefault(
                query_id,
                {"query": row["query"], "labels": {}},
            )
            grouped[query_id]["labels"][row["news_id"]] = int(row["relevance"])
    return grouped


def evaluate(labels: dict[str, dict[str, Any]], mode: str, k: int) -> dict[str, float]:
    recall_values = []
    mrr_values = []
    ndcg_values = []

    for payload in labels.values():
        query = payload["query"]
        relevance_by_id = payload["labels"]
        results = _search(query=query, mode=mode, k=k)
        ranked_ids = [str(result.get("news_id") or "") for result in results[:k]]

        recall_values.append(recall_at_k(ranked_ids, relevance_by_id))
        mrr_values.append(mrr_at_k(ranked_ids, relevance_by_id))
        ndcg_values.append(ndcg_at_k(ranked_ids, relevance_by_id, k=k))

    return {
        "queries": len(labels),
        "recall": _mean(recall_values),
        "mrr": _mean(mrr_values),
        "ndcg": _mean(ndcg_values),
    }


def recall_at_k(ranked_ids: list[str], relevance_by_id: dict[str, int]) -> float:
    relevant_ids = {news_id for news_id, rel in relevance_by_id.items() if rel > 0}
    if not relevant_ids:
        return 0.0
    hits = relevant_ids.intersection(ranked_ids)
    return len(hits) / len(relevant_ids)


def mrr_at_k(ranked_ids: list[str], relevance_by_id: dict[str, int]) -> float:
    for rank, news_id in enumerate(ranked_ids, start=1):
        if relevance_by_id.get(news_id, 0) > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevance_by_id: dict[str, int], k: int) -> float:
    gains = [relevance_by_id.get(news_id, 0) for news_id in ranked_ids[:k]]
    dcg = _dcg(gains)
    ideal_gains = sorted(relevance_by_id.values(), reverse=True)[:k]
    ideal_dcg = _dcg(ideal_gains)
    if ideal_dcg == 0:
        return 0.0
    return dcg / ideal_dcg


def _search(query: str, mode: str, k: int) -> list[dict[str, Any]]:
    if mode == "vector":
        from search import vector_search

        return vector_search(query, top_k=k, score_threshold=None)

    from hybrid_search import retrieve_and_rerank

    return retrieve_and_rerank(
        query=query,
        candidate_k=max(50, k),
        final_k=k,
        score_threshold=None,
        use_reranker=True,
    )


def _dcg(gains: list[int]) -> float:
    return sum((2**gain - 1) / math.log2(index + 2) for index, gain in enumerate(gains))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


if __name__ == "__main__":
    main()
