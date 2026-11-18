"""End-to-end ingestion and indexing pipeline.

Executes:
1. Normalize scraped data (DarGlobal & Wasalt)
2. Generate structured chunks
3. Compute embeddings using Sentence Transformers
4. Upsert into Qdrant vector database

Run:
  python -m app.ingestion.indexer
"""
from __future__ import annotations

import time
from app.ingestion.normalize import normalize_all
from app.ingestion.chunker import chunk_all
from app.rag.embeddings import embed_texts
from app.rag.vector_store import upsert_chunks, count_collection


def run_pipeline() -> dict:
    t0 = time.time()
    print("=" * 60)
    print("PROPERTY INTELLIGENCE AI - DATA INGESTION & INDEXING")
    print("=" * 60)

    # Step 1: Normalize
    print("\n[Step 1/4] Normalizing raw scraped datasets...")
    properties, docs = normalize_all()

    # Step 2: Chunk
    print("\n[Step 2/4] Chunking structured properties & knowledge documents...")
    chunks = chunk_all()
    texts = [c["text"] for c in chunks]

    # Step 3: Embed
    print(f"\n[Step 3/4] Generating embeddings for {len(texts)} chunks...")
    vectors = embed_texts(texts, batch_size=32)
    print(f"Computed {len(vectors)} embeddings (dim: {len(vectors[0]) if vectors else 0})")

    # Step 4: Index into Qdrant
    print(f"\n[Step 4/4] Upserting into Qdrant vector collection...")
    upserted_count = upsert_chunks(chunks, vectors)
    total_in_db = count_collection()

    elapsed = round(time.time() - t0, 2)
    print("\n" + "=" * 60)
    print(f"INDEXING COMPLETE in {elapsed}s")
    print(f"Total Chunks Upserted: {upserted_count}")
    print(f"Current Collection Size: {total_in_db}")
    print("=" * 60)

    return {
        "status": "success",
        "properties_count": len(properties),
        "docs_count": len(docs),
        "chunks_indexed": upserted_count,
        "collection_total": total_in_db,
        "elapsed_seconds": elapsed
    }


if __name__ == "__main__":
    run_pipeline()
