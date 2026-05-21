import json

from config import IMAGE_FOLDER
from ingest import load_image_collection
from search import image_search


if __name__ == "__main__":
    stats = load_image_collection(reset=False)

    sample_image = IMAGE_FOLDER / "news_20260519_0001.jpg"
    print("Sample image search:")
    for result in image_search(sample_image, top_k=3, score_threshold=0.5):
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if stats["skipped_existing"]:
        print("Duplicate prevention is active.")
