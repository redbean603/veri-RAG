# Repository Guidelines

## Project Structure & Module Organization

This repository contains the Veri-RAG Vector DB component for Agent-provided text vectors, optional image vectors, and evidence retrieval over Chroma.

- `config.py`: Chroma host, collection names, model names, and data paths.
- `embeddings.py`: OpenAI text embedding fallback.
- `search.py`: Agent-facing search functions: `agent_evidence_search()`, `vector_search()`, and `evidence_search()`.
- `ingest.py`: Text/image-vector ingestion, Agent JSON upsert helpers, duplicate checks, metadata cleanup, and Chroma insert logic.
- `hybrid_search.py`: Candidate retrieval, keyword matching, reciprocal-rank fusion, and rerank orchestration.
- `reranker.py`: Optional local `FlagEmbedding` reranker with vector-score fallback behavior.
- `agent_json/`: Current Agent-provided JSON records named like `naver_20260526080123_007_result.json`.

There is currently no dedicated `tests/` directory.

## Build, Test, and Development Commands

Install dependencies if needed:

```bash
pip install chromadb openai python-dotenv torch torchvision transformers Pillow
```

Install the optional reranker dependency only when local reranking is needed:

```bash
pip install FlagEmbedding
```

Compile-check the Python modules:

```bash
python -m py_compile config.py embeddings.py search.py ingest.py
python -m py_compile reranker.py hybrid_search.py
```

Call Agent-facing search directly:

```bash
python -c "from search import vector_search; print(vector_search('holding company stock price'))"
python -c "from search import evidence_search; print(evidence_search('holding company stock price', query_vector=[0.0]*1536, candidate_news_ids=['naver_20260526080123_007'], candidate_k=5, final_k=2, use_reranker=False))"
python -c "from search import agent_evidence_search; print(agent_evidence_search(query='holding company stock price', query_vector=[0.0]*1536, candidate_news_ids=[], final_k=2, use_reranker=False))"
```

## Coding Style & Naming Conventions

Use Python 3.14-compatible code with 4-space indentation and type hints for public functions. Keep modules small and role-based:

- Configuration belongs in `config.py`.
- Model calls belong in `embeddings.py`.
- Agent-facing retrieval belongs in `search.py`.
- Persistence and Chroma writes belong in `ingest.py`.
- Hybrid retrieval/reranking orchestration belongs in `hybrid_search.py`.
- Reranker model loading and fallback behavior belongs in `reranker.py`.

Use snake_case for functions and variables, uppercase names for constants, and stable IDs based on `news_id`. Preserve the current Agent JSON file naming convention: `{news_id}_result.json`.

## Retrieval Behavior

Agent integration should call `agent_evidence_search()` when the Agent passes incoming JSON files or records, graph-selected `candidate_news_ids`, `query`, and optionally `query_vector`. The function upserts JSON records into Chroma, runs evidence retrieval, and returns `selected_news_ids`, ranked result evidence, and ingest stats.

Incoming Agent JSON records should include `text_vector` and may include `image_vector`:

```json
{
  "news_id": "naver_20260526080123_007",
  "summary": "Evidence summary text",
  "text_vector": [0.01, -0.02, 0.03],
  "image_vector": [0.04, -0.05, 0.06]
}
```

`text_vector` is required and stored directly. `image_vector` is optional; when present, it is upserted into the image collection with the same `news_id`, and when absent image upsert is skipped. The Agent does not send image files. If Agent code passes `query_vector`, text retrieval does not need an OpenAI API key. `query_vector` and `text_vector` must come from the same embedding model and have the same dimension.

`vector_search()` returns formatted dictionaries with `news_id`, metadata, `content`, `summary`, cosine-derived `score`, and raw `distance`.

`evidence_search()` delegates to `hybrid_search.retrieve_and_rerank()`. It accepts optional graph-selected `candidate_news_ids`, retrieves a larger vector candidate set within that candidate set, runs keyword matching over current Agent JSON summaries in `agent_json/`, fuses candidates with RRF, and optionally reranks with `LocalReranker`.

Current keyword search is a lightweight token-matching implementation over `summary` first, then `title`/`content` fallback. It is not BM25 yet.

When `FlagEmbedding` or the reranker model is unavailable, the reranker must return vector-score ordered results with `rank_stage="vector_fallback"` instead of failing the Agent workflow.

## Testing Guidelines

No formal test framework is configured yet. For now, validate changes with:

```bash
python -m py_compile config.py embeddings.py search.py ingest.py
python -m py_compile reranker.py hybrid_search.py
```

Mock OpenAI, Chroma, and reranker calls when adding unit tests.

When adding tests, prefer `pytest` and place files under `tests/` with names like `test_search.py`, `test_ingest.py`, or `test_reranker.py`. Use the EC2 or remote Chroma server only for explicit integration checks.

## Commit & Pull Request Guidelines

Use concise imperative commit messages, for example `Add image search threshold filtering`.

Pull requests should include:

- Summary of behavior changes.
- Verification commands and results.
- Any changes to Chroma collections, data formats, or environment variables.
- Any changes to Agent-facing interfaces or return fields.
- Notes for preprocessing pipeline consumers when field names, paths, or naming conventions change.

## Security & Configuration Tips

Keep API keys in `.env`; do not hard-code or commit secrets. The Chroma server is configured in `config.py` as `100.55.254.41:8000`. If changing hosts, ports, collection names, model names, or data paths, update `config.py`, `README.md`, and this file together.

Be careful with collection resets. `load_text_collection(reset=True)` deletes and recreates the text Chroma collection.
