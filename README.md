# Veri-RAG Vector DB

Vector retrieval component for Veri-RAG. This repository stores Agent-provided text and optional image vectors in Chroma and exposes Python search functions for Agent-side evidence retrieval. The primary Agent integration path accepts incoming JSON records, graph-selected candidate `news_id` values, `query`, and required `query_vector`, then returns final selected `news_id` values with ranking evidence.

## Current Status

- Chroma server: `100.55.254.41:8000`
- Text collection: `news_text_agent`
- Image collection: `news_image_clip`
- Text/query embeddings: provided by the Agent or upstream pipeline; this codebase does not call OpenAI
- Image embedding model: optional externally provided `image_vector`
- Chroma distance space: cosine
- Local reranker: `BAAI/bge-reranker-v2-m3` through optional `FlagEmbedding`
- Data paths:
  - Agent JSON records: `agent_json/`

## Project Structure

```text
veri-rag-vectordb/
|-- config.py                 # Chroma host, collections, model names, and data paths
|-- search.py                 # Agent-facing agent_evidence_search(), vector_search(), evidence_search()
|-- ingest.py                 # Text/image-vector ingestion, Agent JSON upsert helpers, metadata cleanup
|-- hybrid_search.py          # Candidate retrieval, keyword matching, fusion, reranking
|-- reranker.py               # Optional local FlagEmbedding reranker with fallback behavior
|-- AGENTS.md                 # Contributor and agent instructions
`-- agent_json/               # Current Agent-provided JSON records
```

## Data Convention

Current retrieval uses only Agent-provided JSON records in the `naver_20260526080123_007_result.json` shape.

Agent JSON records are stored under `agent_json/` when `persist_json=True` and should include a stable `news_id`.

```json
{
  "news_id": "naver_20260526080123_007",
  "summary": "News summary or evidence text",
  "text_vector": [0.01, -0.02, 0.03],
  "image_vector": [0.04, -0.05, 0.06]
}
```

Optional metadata fields are preserved when present: `title`, `published_at`, `source`, `url`, `topic`, `entities`, `claim_type`, `source_type`, `modality`, and `event_id`.

Agent upsert requires `summary` and `text_vector` and stores the vector directly. Agent search requires `query_vector`; this repository does not create query embeddings. The `query_vector` model and dimension must match `text_vector`.

`text_vector` is required for the current Agent JSON path. `image_vector` is optional. If present, it is upserted into the image collection with the same `news_id`; if absent, image upsert is skipped. The Agent does not send image files.

## Setup

Install core dependencies:

```bash
pip install chromadb
```

Install the optional local reranker dependency when reranking is needed:

```bash
pip install FlagEmbedding
```

No OpenAI API key is used by this component. The Agent or upstream embedding service must provide `query_vector` and `text_vector`.

## Ingestion

Maintenance-only bulk load from `agent_json/`:

```bash
python -c "from ingest import load_text_collection; print(load_text_collection(reset=False))"
```

Agent-path upsert of provided JSON files:

```bash
python -c "from ingest import ingest_text_json_files; print(ingest_text_json_files(['naver_20260526080123_007_result.json']))"
```

Set `reset=True` only for maintenance when you intentionally want to delete and rebuild the text Chroma collection. The normal Agent path is `agent_evidence_search()`, which upserts only records or files passed by the Agent.

## Agent Search Interface

Use `search.py` from Agent code. For end-to-end Agent integration, call `agent_evidence_search()`.

```python
from search import agent_evidence_search, evidence_search, vector_search

agent_results = agent_evidence_search(
    query="holding company stock price policy momentum",
    query_vector=[0.01, -0.02, 0.03],
    candidate_news_ids=[
        "naver_20260526080123_007",
        "naver_20260526080123_008",
    ],
    json_files=[
        "naver_20260526080123_007_result.json",
        "naver_20260526080123_008_result.json",
    ],
    final_k=5,
)

selected_news_ids = agent_results["selected_news_ids"]
evidence = agent_results["results"]
```

The Agent may pass records directly instead of file paths:

```python
agent_results = agent_evidence_search(
    query="holding company stock price policy momentum",
    query_vector=[0.01, -0.02, 0.03],
    candidate_news_ids=["naver_20260526080123_007"],
    json_records=[
        {
            "news_id": "naver_20260526080123_007",
            "summary": "News summary or evidence text",
            "text_vector": [0.01, -0.02, 0.03],
            "image_vector": [0.04, -0.05, 0.06],
        }
    ],
    final_k=5,
)
```

Lower-level search functions remain available:

```python
from search import evidence_search, vector_search

text_results = vector_search(
    query="holding company stock price",
    query_vector=[0.01, -0.02, 0.03],
    top_k=3,
    score_threshold=0.3,
)

evidence_results = evidence_search(
    query="holding company stock price policy momentum",
    query_vector=[0.01, -0.02, 0.03],
    candidate_news_ids=[
        "naver_20260526080123_007",
        "naver_20260526080123_008",
    ],
    candidate_k=50,
    final_k=5,
    use_reranker=True,
)
```

`agent_evidence_search()` does three steps for the Agent:

```text
incoming JSON files or records -> validate required fields -> Chroma text upsert
graph candidate_news_ids + query/query_vector -> evidence_search()
final selected news_id list + ranking evidence -> Agent return payload
```

Agent return payload:

```python
{
    "selected_news_ids": [
        "naver_20260526080123_007"
    ],
    "results": [
        {
            "news_id": "naver_20260526080123_007",
            "summary": "News summary or evidence text",
            "similarity_score": 0.83,
            "distance": 0.17,
            "fusion_score": 0.032,
            "rerank_score": 1.42,
            "rank_stage": "reranked"
        }
    ],
    "ingest": {
        "loaded": 1,
        "load_failed": 0,
        "upserted": 1,
        "image_upserted": 1,
        "skipped_empty": 0,
        "skipped_image_vector": 0,
        "failed": 0,
        "invalid": 0,
        "excluded_from_search": 0
    },
    "failed_news_ids": [],
    "ingest_errors": []
}
```

Core result fields:

```python
[
    {
        "news_id": "naver_20260526080123_007",
        "title": "News title or summary fallback",
        "url": "https://...",
        "published_at": "2026-05-19 16:53:11",
        "source": "src_naver",
        "image_path": "",
        "content": "News summary or evidence text",
        "summary": "News summary or evidence text",
        "score": 0.53,
        "distance": 0.47
    }
]
```

`score_threshold` filters out results with `score < score_threshold`.

`evidence_search()` keeps `vector_search()` intact. It accepts graph-selected `candidate_news_ids` and a required precomputed `query_vector`, restricts vector and keyword retrieval to that candidate set, fuses both candidate lists with RRF, and reranks locally. If `query_vector` is omitted, search raises `ValueError`. If `candidate_news_ids=None`, it searches the full text collection. If `candidate_news_ids=[]`, it returns no results.

Current keyword search is lightweight token matching over Chroma documents and metadata, using `summary` first with `title`/`content` fallback. It is not BM25 yet and no longer depends on local `agent_json/` files.

When reranking succeeds, evidence results include:

```python
{
    "rerank_score": 1.23,
    "rank_stage": "reranked"
}
```

If `FlagEmbedding` or the reranker model is unavailable, retrieval falls back to fusion/vector-score ordering and marks results with:

```python
{
    "rank_stage": "vector_fallback"
}
```

## Verification

Compile-check the active modules:

```bash
python -m py_compile config.py search.py ingest.py
python -m py_compile reranker.py hybrid_search.py
```

Run direct search smoke checks:

```bash
python -c "from search import vector_search; print(vector_search('holding company stock price', query_vector=[0.0]*1536, top_k=2, score_threshold=0.0))"
python -c "from search import evidence_search; print(evidence_search('holding company stock price', query_vector=[0.0]*1536, candidate_k=5, final_k=2, use_reranker=False))"
python -c "from search import agent_evidence_search; print(agent_evidence_search(query='holding company stock price', query_vector=[0.0]*1536, candidate_news_ids=[], final_k=2, use_reranker=False))"
```

## Notes for Pipeline Integration

Coordinate these details before connecting a preprocessing pipeline or Agent runtime:

- JSON field names and required metadata.
- Optional `image_vector` presence and embedding dimension.
- Batch execution or file-watch ingestion behavior.
- Python import interface versus an HTTP API wrapper.
- Default `top_k`, `candidate_k`, `final_k`, and score thresholds.
- Any Chroma host, collection, model, or metadata schema changes.
