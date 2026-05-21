# Repository Guidelines

## Project Structure & Module Organization

This repository contains the Veri-RAG Vector DB component for text and image retrieval over Chroma.

- `config.py`: Chroma host, collection names, model names, and data paths.
- `embeddings.py`: OpenAI text embeddings and CLIP image embeddings.
- `search.py`: Agent-facing search functions, including `vector_search()` and `image_search()`.
- `ingest.py`: Image ingestion, duplicate checks, metadata cleanup, and Chroma insert logic.
- `main.py`: Local smoke-run entry point for ingestion and sample image search.
- `processed_news_backup/`: Processed JSON records named like `news_20260519_0001_result.json`.
- `raw_news_backup/`: Source images and text files named like `news_20260519_0001.jpg`.

There is currently no dedicated `tests/` directory.

## Build, Test, and Development Commands

Run the local ingestion/search smoke test:

```bash
python main.py
```

Compile-check the Python modules:

```bash
python -m py_compile config.py embeddings.py search.py ingest.py main.py
```

Call the Agent-facing text search directly:

```bash
python -c "from search import vector_search; print(vector_search('지주회사 주가'))"
```

Install dependencies if needed:

```bash
pip install chromadb openai python-dotenv torch torchvision transformers Pillow
```

## Coding Style & Naming Conventions

Use Python 3.14-compatible code with 4-space indentation and type hints for public functions. Keep modules small and role-based: configuration in `config.py`, model calls in `embeddings.py`, retrieval in `search.py`, and persistence in `ingest.py`.

Use snake_case for functions and variables, uppercase names for constants, and stable IDs based on `news_id`. Preserve the current file naming convention: `news_YYYYMMDD_0001_result.json` maps to `news_YYYYMMDD_0001.jpg`.

## Testing Guidelines

No formal test framework is configured yet. For now, validate changes with:

```bash
python -m py_compile config.py embeddings.py search.py ingest.py main.py
python main.py
```

When adding tests, prefer `pytest` and place files under `tests/` with names like `test_search.py` or `test_ingest.py`. Mock OpenAI and Chroma calls where possible; use the EC2 Chroma server only for integration checks.

## Commit & Pull Request Guidelines

This folder does not currently include Git history, so no existing commit convention can be inferred. Use concise imperative commit messages, for example `Add image search threshold filtering`.

Pull requests should include:

- Summary of behavior changes.
- Verification commands and results.
- Any changes to Chroma collections, data formats, or environment variables.
- Notes for Agent or preprocessing pipeline consumers when interfaces change.

## Security & Configuration Tips

Keep API keys in `.env`; do not hard-code or commit secrets. The Chroma server is configured in `config.py` as `3.93.218.110:8000`. If changing hosts, ports, collection names, or model names, update `config.py` and mention the change in the PR.
