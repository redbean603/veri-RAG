from pathlib import Path


CHROMA_HOST = "3.93.218.110"
CHROMA_PORT = 8000

TEXT_COLLECTION = "news_text_openai"
IMAGE_COLLECTION = "news_image_clip"

TEXT_EMBEDDING_MODEL = "text-embedding-3-small"
CLIP_MODEL = "openai/clip-vit-base-patch32"

JSON_FOLDER = Path("processed_news_backup")
IMAGE_FOLDER = Path("raw_news_backup")
