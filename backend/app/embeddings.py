from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import numpy as np
from PIL.Image import Image as PILImage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.settings import get_settings


_openai_client = None  # lazy-initialized OpenAI client
_image_model = None  # lazy-initialized SentenceTransformer model


def _normalize_text_for_cache(text: str) -> str:
    text_stripped = text.strip().lower()
    # collapse all whitespace to a single space for better cache hits
    return re.sub(r"\s+", " ", text_stripped)


def _get_openai_client():  # type: ignore[no-untyped-def]
    global _openai_client
    if _openai_client is None:
        # OpenAI SDK v1 style client
        from openai import OpenAI  # imported lazily to speed cold starts

        settings = get_settings()
        if settings.openai_api_key:
            _openai_client = OpenAI(api_key=settings.openai_api_key)
        else:
            _openai_client = OpenAI()
    return _openai_client


@retry(reraise=True, wait=wait_exponential(multiplier=0.5, min=1, max=10), stop=stop_after_attempt(5))
def _fetch_text_embedding(text: str) -> list[float]:
    client = _get_openai_client()
    settings = get_settings()
    response = client.embeddings.create(model=settings.embedding_model, input=text)
    vec = response.data[0].embedding
    # ensure Python floats (not numpy types)
    return [float(x) for x in vec]


@lru_cache(maxsize=256)
def _cached_text_embedding(normalized_text: str) -> tuple[float, ...]:
    embedding = _fetch_text_embedding(normalized_text)
    # cache must return hashable; store as tuple
    return tuple(float(x) for x in embedding)


def get_text_embedding(text: str) -> list[float]:
    normalized_text = _normalize_text_for_cache(text)
    return list(_cached_text_embedding(normalized_text))


def _get_image_model():  # type: ignore[no-untyped-def]
    global _image_model
    if _image_model is None:
        from sentence_transformers import SentenceTransformer  # lazy import

        # CLIP ViT-B/32 returns 512-dim embeddings
        _image_model = SentenceTransformer("clip-ViT-B-32")
    return _image_model


def get_image_embedding(pil_image: PILImage) -> list[float]:
    model = _get_image_model()
    # Ensure RGB for consistency across inputs
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    vec = model.encode(
        pil_image,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    if isinstance(vec, list):  # defensive: SentenceTransformer may return list
        vec = np.asarray(vec)
    vec = vec.astype(np.float32)
    return vec.tolist()


