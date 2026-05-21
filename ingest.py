import json
from pathlib import Path
from typing import Any

from config import IMAGE_COLLECTION, IMAGE_FOLDER, JSON_FOLDER
from embeddings import get_image_embedding
from search import get_chroma_client, get_image_collection, get_text_collection


def load_image_collection(reset: bool = False) -> dict[str, int]:
    if reset:
        _reset_image_collection()

    image_collection = get_image_collection()
    stats = {"inserted": 0, "skipped_existing": 0, "skipped_missing": 0, "failed": 0}

    for json_path in sorted(JSON_FOLDER.glob("*_result.json")):
        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        news_id = data["news_id"]
        image_path = IMAGE_FOLDER / json_path.name.replace("_result.json", ".jpg")

        if _id_exists(image_collection, news_id):
            stats["skipped_existing"] += 1
            print(f"Skipped existing image embedding: {news_id}")
            continue

        if not image_path.exists():
            stats["skipped_missing"] += 1
            print(f"Skipped missing image: {news_id} path={image_path}")
            continue

        try:
            embedding = get_image_embedding(image_path)
            image_collection.add(
                ids=[news_id],
                embeddings=[embedding],
                documents=[data.get("title", "")],
                metadatas=[_clean_metadata(data, image_path)],
            )
            stats["inserted"] += 1
            print(f"Saved image embedding: {news_id} dims={len(embedding)}")
        except Exception as exc:
            stats["failed"] += 1
            print(f"Image save error: {news_id} - {type(exc).__name__}: {exc}")

    print(f"Text collection count: {get_text_collection().count()}")
    print(f"Image collection count: {image_collection.count()}")
    print(f"Image ingest stats: {stats}")
    return stats


def _reset_image_collection():
    client = get_chroma_client()
    try:
        client.delete_collection(IMAGE_COLLECTION)
        print("Deleted existing image collection")
    except Exception:
        pass


def _id_exists(collection, doc_id: str) -> bool:
    result = collection.get(ids=[doc_id], include=[])
    return bool(result.get("ids"))


def _clean_metadata(data: dict[str, Any], image_path: Path) -> dict[str, str]:
    metadata = {
        "title": data.get("title", ""),
        "published_at": data.get("published_at", ""),
        "source": data.get("source", ""),
        "url": data.get("url", ""),
        "image_path": str(image_path),
    }
    return {key: "" if value is None else str(value) for key, value in metadata.items()}
