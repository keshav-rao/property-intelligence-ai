"""Embeddings generator using Sentence Transformers.

Default model: BAAI/bge-small-en-v1.5 (384 dimensions, fast & accurate).
Fallback: sentence-transformers/all-MiniLM-L6-v2.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np

_model = None
MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception:
            # Fallback to standard lightweight model
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: Sequence[str], batch_size: int = 32) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    model = get_embedding_model()
    # For bge models, query instruction can be prepended or direct
    emb = model.encode(query, normalize_embeddings=True)
    return emb.tolist()
