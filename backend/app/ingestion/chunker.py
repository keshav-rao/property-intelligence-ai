"""Document chunker for Property Intelligence AI.

Produces structured chunks ready for vector embedding and hybrid retrieval:
- Preserves complete property context in each property chunk
- Chunks knowledge documents and FAQs with parent metadata
"""
from __future__ import annotations

import json
from pathlib import Path
from app.config import get_data_dir

PROCESSED_DIR = get_data_dir() / "processed"


def build_property_chunk(prop: dict) -> dict:
    amenities_str = ", ".join(prop.get("amenities", [])) if prop.get("amenities") else "Standard residential amenities"
    brand_str = f" | Brand Partner: {prop['brand_partner']}" if prop.get("brand_partner") else ""
    dev_str = f"Developer: {prop.get('developer', 'N/A')}{brand_str}"

    text = (
        f"PROPERTY: {prop.get('name') or prop.get('title')}\n"
        f"PLATFORM: {prop.get('platform', '').upper()}\n"
        f"LOCATION: {prop.get('city', '')}, {prop.get('country', '')}"
        + (f" ({prop.get('district')})" if prop.get("district") else "")
        + f"\nTYPE: {prop.get('property_type', 'Residential')} | PURPOSE: For {prop.get('purpose', 'Sale').title()}\n"
        f"PRICE: {prop.get('price_display', 'Contact for Price')}\n"
        + (f"BEDROOMS: {prop.get('bedrooms')} | " if prop.get("bedrooms") is not None else "")
        + (f"AREA: {prop.get('area_sqm')} SQM\n" if prop.get("area_sqm") else "\n")
        + f"{dev_str}\n"
        f"AMENITIES: {amenities_str}\n"
        f"DESCRIPTION: {prop.get('description', '')}\n"
        + (f"INVESTMENT HIGHLIGHTS: {prop.get('investment_highlights')}\n" if prop.get("investment_highlights") else "")
        + f"SOURCE URL: {prop.get('url')}\n"
        f"SCRAPED AT: {prop.get('scraped_at')}"
    )

    return {
        "id": f"chunk-prop-{prop['id']}",
        "parent_id": prop["id"],
        "kind": "property",
        "platform": prop.get("platform"),
        "title": prop.get("title") or prop.get("name"),
        "city": (prop.get("city") or "").lower(),
        "country": prop.get("country", ""),
        "property_type": (prop.get("property_type") or "").lower(),
        "purpose": (prop.get("purpose") or "sale").lower(),
        "price_numeric": prop.get("price_numeric", 0),
        "currency": prop.get("currency", "SAR"),
        "url": prop.get("url"),
        "scraped_at": prop.get("scraped_at"),
        "text": text.strip(),
        "property_data": prop
    }


def build_knowledge_chunks(doc: dict) -> list[dict]:
    chunks = []
    text = doc.get("text", "").strip()
    if not text:
        return chunks

    # If the text has FAQs or paragraphs, split into reasonable sections
    sections = [s.strip() for s in text.split("\n\n") if len(s.strip()) > 40]
    if not sections:
        sections = [text]

    for idx, sec in enumerate(sections):
        chunk_text = (
            f"SOURCE DOCUMENT: {doc.get('title')}\n"
            f"PLATFORM: {doc.get('platform', '').upper()}\n"
            f"TOPIC / SECTION:\n{sec}\n"
            f"SOURCE URL: {doc.get('url')}\n"
            f"SCRAPED AT: {doc.get('scraped_at')}"
        )
        chunks.append({
            "id": f"chunk-doc-{doc['id']}-{idx}",
            "parent_id": doc["id"],
            "kind": "knowledge",
            "platform": doc.get("platform"),
            "title": doc.get("title"),
            "city": (doc.get("city") or "").lower(),
            "country": "Saudi Arabia" if doc.get("platform") == "wasalt" else "Global",
            "property_type": "knowledge",
            "purpose": "info",
            "price_numeric": 0,
            "currency": "",
            "url": doc.get("url"),
            "scraped_at": doc.get("scraped_at"),
            "text": chunk_text.strip(),
            "property_data": None
        })
    return chunks


def chunk_all() -> list[dict]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []

    # Process properties
    props_file = PROCESSED_DIR / "properties.json"
    if props_file.exists():
        with open(props_file, "r", encoding="utf-8") as f:
            properties = json.load(f)
        for p in properties:
            all_chunks.append(build_property_chunk(p))
        print(f"[Chunker] Generated {len(properties)} property chunks")

    # Process knowledge documents
    docs_file = PROCESSED_DIR / "knowledge_docs.json"
    if docs_file.exists():
        with open(docs_file, "r", encoding="utf-8") as f:
            docs = json.load(f)
        doc_chunk_count = 0
        for d in docs:
            kchunks = build_knowledge_chunks(d)
            all_chunks.extend(kchunks)
            doc_chunk_count += len(kchunks)
        print(f"[Chunker] Generated {doc_chunk_count} knowledge chunks from {len(docs)} documents")

    chunks_out = PROCESSED_DIR / "chunks.json"
    with open(chunks_out, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"[Chunker] Saved total {len(all_chunks)} chunks to {chunks_out}")
    return all_chunks


if __name__ == "__main__":
    chunk_all()
