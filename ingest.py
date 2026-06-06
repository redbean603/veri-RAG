import json
from pathlib import Path
from typing import Any

from config import JSON_FOLDER, TEXT_COLLECTION
from search import get_chroma_client, get_image_collection, get_text_collection


def ingest_text_records(
    records: list[dict[str, Any]],
    persist_json: bool = True,
) -> dict[str, int]:
    text_collection = get_text_collection()
    image_collection = get_image_collection()
    stats = {
        "upserted": 0,
        "image_upserted": 0,
        "skipped_empty": 0,
        "skipped_image_vector": 0,
        "failed": 0,
    }

    for data in records:
        news_id = str(data.get("news_id") or "")
        content = _text_document(data)
        if not news_id or not content:
            stats["skipped_empty"] += 1
            continue

        try:
            embedding = _text_embedding(data)
            text_collection.upsert(
                ids=[news_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[_clean_metadata(data, modality="text")],
            )
            image_vector = _optional_vector(data, "image_vector")
            if image_vector is not None:
                image_collection.upsert(
                    ids=[news_id],
                    embeddings=[image_vector],
                    documents=[_display_title(data)],
                    metadatas=[_clean_metadata(data, modality="image")],
                )
                stats["image_upserted"] += 1
            else:
                stats["skipped_image_vector"] += 1

            if persist_json:
                _persist_text_record(data)
            stats["upserted"] += 1
        except Exception as exc:
            stats["failed"] += 1
            print(f"Text upsert error: {news_id or '<missing news_id>'} - {type(exc).__name__}: {exc}")

    return stats


def ingest_text_json_files(
    json_files: list[str | Path],
    persist_json: bool = True,
) -> dict[str, int]:
    records = []
    stats = {"loaded": 0, "load_failed": 0}
    for json_file in json_files:
        path = _resolve_json_path(json_file)
        try:
            with path.open("r", encoding="utf-8") as file:
                records.append(json.load(file))
            stats["loaded"] += 1
        except (OSError, json.JSONDecodeError) as exc:
            stats["load_failed"] += 1
            print(f"JSON load error: {path} - {type(exc).__name__}: {exc}")

    ingest_stats = ingest_text_records(records, persist_json=persist_json)
    return {**stats, **ingest_stats}


def load_text_collection(reset: bool = False) -> dict[str, int]:
    if reset:
        _reset_text_collection()

    text_collection = get_text_collection()
    stats = {"inserted": 0, "skipped_existing": 0, "skipped_empty": 0, "failed": 0}

    for json_path in sorted(JSON_FOLDER.glob("*_result.json")):
        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        news_id = data["news_id"]
        content = _text_document(data)

        if _id_exists(text_collection, news_id):
            stats["skipped_existing"] += 1
            print(f"Skipped existing text embedding: {news_id}")
            continue

        if not content:
            stats["skipped_empty"] += 1
            print(f"Skipped empty text: {news_id}")
            continue

        try:
            embedding = _text_embedding(data)
            text_collection.add(
                ids=[news_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[_clean_metadata(data, modality="text")],
            )
            stats["inserted"] += 1
            print(f"Saved text embedding: {news_id} dims={len(embedding)}")
        except Exception as exc:
            stats["failed"] += 1
            print(f"Text save error: {news_id} - {type(exc).__name__}: {exc}")

    print(f"Text collection count: {text_collection.count()}")
    return stats


def _reset_text_collection():
    client = get_chroma_client()
    try:
        client.delete_collection(TEXT_COLLECTION)
        print("Deleted existing text collection")
    except Exception:
        pass


def _id_exists(collection, doc_id: str) -> bool:
    result = collection.get(ids=[doc_id], include=[])
    return bool(result.get("ids"))


def _clean_metadata(
    data: dict[str, Any],
    image_path: Path | None = None,
    modality: str = "image",
) -> dict[str, str]:
    metadata = {
        "news_id": data.get("news_id", ""),
        "title": _display_title(data),
        "summary": data.get("summary", ""),
        "published_at": data.get("published_at", ""),
        "source": data.get("source", ""),
        "url": data.get("url", ""),
        "image_path": "" if image_path is None else str(image_path),
        "topic": data.get("topic"),
        "entities": data.get("entities"),
        "claim_type": data.get("claim_type"),
        "source_type": data.get("source_type"),
        "modality": data.get("modality", modality),
        "event_id": data.get("event_id"),
    }
    return {key: "" if value is None else str(value) for key, value in metadata.items()}


def _text_document(data: dict[str, Any]) -> str:
    summary = str(data.get("summary") or "").strip()
    if summary:
        return summary

    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    return "\n".join(part for part in (title, content) if part)


def _display_title(data: dict[str, Any]) -> str:
    return str(data.get("title") or data.get("summary") or "")


def _text_embedding(data: dict[str, Any]) -> list[float]:
    vector = _optional_vector(data, "text_vector")
    if vector is None:
        raise ValueError("text_vector is required")
    return vector


def _persist_text_record(data: dict[str, Any]) -> None:
    news_id = str(data.get("news_id") or "")
    if not news_id:
        return
    JSON_FOLDER.mkdir(parents=True, exist_ok=True)
    json_path = JSON_FOLDER / f"{news_id}_result.json"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def _resolve_json_path(json_file: str | Path) -> Path:
    path = Path(json_file)
    candidates = [path]
    if path.suffix != ".json":
        candidates.append(path.with_suffix(".json"))
    if not path.is_absolute():
        candidates.append(JSON_FOLDER / path)
        if path.suffix != ".json":
            candidates.append(JSON_FOLDER / path.with_suffix(".json"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def _optional_vector(data: dict[str, Any], field: str) -> list[float] | None:
    vector = data.get(field)
    if vector is None:
        return None
    if not isinstance(vector, list) or not all(isinstance(value, int | float) for value in vector):
        raise ValueError(f"{field} must be a list of numbers")
    return [float(value) for value in vector]
