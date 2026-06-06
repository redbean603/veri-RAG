from pathlib import Path


CHROMA_HOST = "100.55.254.41"
CHROMA_PORT = 8000

TEXT_COLLECTION = "news_text_openai"
IMAGE_COLLECTION = "news_image_clip"

TEXT_EMBEDDING_MODEL = "text-embedding-3-small"
CLIP_MODEL = "openai/clip-vit-base-patch32"

JSON_FOLDER = Path("agent_json")
IMAGE_FOLDER = Path("agent_images")

