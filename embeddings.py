import os
from pathlib import Path

import torch
import torch.nn.functional as F
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from config import CLIP_MODEL, TEXT_EMBEDDING_MODEL


load_dotenv()

_openai_client: OpenAI | None = None
_clip_model: CLIPModel | None = None
_clip_processor: CLIPProcessor | None = None


def get_text_embedding(text: str) -> list[float]:
    client = _get_openai_client()
    response = client.embeddings.create(
        model=TEXT_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def get_image_embedding(image_path: str | Path) -> list[float]:
    model, processor = _get_clip()
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        output = model.get_image_features(pixel_values=inputs["pixel_values"])

    features = output.pooler_output if hasattr(output, "pooler_output") else output
    embedding = _normalize_vector(features)
    if embedding.numel() != 512:
        raise ValueError(f"Expected CLIP 512-d embedding, got {embedding.numel()} dimensions")
    return embedding.tolist()


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _get_clip() -> tuple[CLIPModel, CLIPProcessor]:
    global _clip_model, _clip_processor
    if _clip_model is None or _clip_processor is None:
        _clip_model = CLIPModel.from_pretrained(CLIP_MODEL)
        _clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
        _clip_model.eval()
    return _clip_model, _clip_processor


def _normalize_vector(vector: torch.Tensor) -> torch.Tensor:
    vector = vector.detach().cpu().float()
    if vector.ndim == 2 and vector.shape[0] == 1:
        vector = vector.squeeze(0)
    if vector.ndim != 1:
        raise ValueError(f"Expected 1D embedding, got shape {tuple(vector.shape)}")
    return F.normalize(vector, dim=0)
