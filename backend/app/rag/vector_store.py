"""Qdrant Vector Database Client and Collection Manager.

Handles collection creation, payload indexing, batch upserts,
and filtered vector similarity queries.
"""
from __future__ import annotations

import uuid
from typing import Any
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings, get_data_dir
from app.rag.embeddings import VECTOR_DIM

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    # Priority 1: Configured URL (e.g. http://qdrant:6333 or http://localhost:6333)
    urls_to_try = [settings.qdrant_url, "http://localhost:6333"]
    for url in urls_to_try:
        try:
            client = QdrantClient(url=url, timeout=1.0, check_compatibility=False)
            client.get_collections()
            _client = client
            return _client
        except Exception:
            continue

    # Priority 2: Local on-disk Qdrant storage (guarantees standalone operation without external service)
    local_path = get_data_dir() / "qdrant_storage"
    local_path.mkdir(parents=True, exist_ok=True)
    _client = QdrantClient(path=str(local_path), check_compatibility=False)
    return _client


def ensure_collection() -> None:
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=VECTOR_DIM,
                distance=qmodels.Distance.COSINE
            )
        )
        # Create payload indexes for metadata filtering
        for field in ["platform", "city", "purpose", "property_type", "kind"]:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
            except Exception:
                pass


def upsert_chunks(chunks: list[dict], vectors: list[list[float]]) -> int:
    ensure_collection()
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    points = []
    for chunk, vec in zip(chunks, vectors):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk["id"]))
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vec,
                payload=chunk
            )
        )

    # Batch upsert in chunks of 64
    batch_size = 64
    total_upserted = 0
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        total_upserted += len(batch)

    return total_upserted


def search_vector_store(
    query_vector: list[float],
    limit: int = 5,
    platform: str | None = None,
    city: str | None = None,
    purpose: str | None = None
) -> list[dict]:
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    must_conditions = []
    if platform and platform in ("darglobal", "wasalt"):
        must_conditions.append(
            qmodels.FieldCondition(key="platform", match=qmodels.MatchValue(value=platform))
        )
    if city and city not in ("all", "global"):
        must_conditions.append(
            qmodels.FieldCondition(key="city", match=qmodels.MatchValue(value=city.lower()))
        )
    if purpose and purpose in ("sale", "rent"):
        must_conditions.append(
            qmodels.FieldCondition(key="purpose", match=qmodels.MatchValue(value=purpose.lower()))
        )

    query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

    try:
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )
            return [
                {
                    "score": r.score,
                    "payload": r.payload
                }
                for r in res.points
            ]
        else:
            results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )
            return [
                {
                    "score": r.score,
                    "payload": r.payload
                }
                for r in results
            ]
    except Exception as e:
        print(f"[VectorStore] Search query error: {e}")
        return []


def count_collection() -> int:
    try:
        client = get_qdrant_client()
        res = client.count(collection_name=settings.qdrant_collection)
        return res.count
    except Exception:
        return 0
