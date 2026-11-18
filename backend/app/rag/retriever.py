"""Hybrid retrieval engine combining vector similarity, lexical keyword boost,
and metadata filtering for DarGlobal and Wasalt data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.rag.embeddings import embed_query
from app.rag.vector_store import search_vector_store

REPO_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = REPO_ROOT / "data" / "processed" / "chunks.json"

_cached_chunks: list[dict] | None = None


def get_all_chunks() -> list[dict]:
    global _cached_chunks
    if _cached_chunks is not None:
        return _cached_chunks
    if CHUNKS_FILE.exists():
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            _cached_chunks = json.load(f)
            return _cached_chunks
    return []


def detect_intent(query: str) -> dict[str, Any]:
    q = query.lower()

    # Platform detection
    darglobal_terms = [
        "darglobal", "dar global", "pagani", "lamborghini", "mouawad", "aston martin",
        "missoni", "w residences", "davinci", "tierra viva", "neptune", "aida",
        "wadi safar", "simaisma", "mulliner", "albert hall", "second home"
    ]
    wasalt_terms = [
        "wasalt", "rental", "rent in", "for rent", "daily rental", "matchmaker",
        "saudi broker", "an nuzhah", "al nuzha", "rega", "flat for rent"
    ]

    has_dg = any(t in q for t in darglobal_terms)
    has_wasalt = any(t in q for t in wasalt_terms)

    platform = None
    if has_dg and not has_wasalt:
        platform = "darglobal"
    elif has_wasalt and not has_dg:
        platform = "wasalt"

    # Comparison intent
    is_comparison = any(w in q for w in ["compare", "comparison", "difference", "versus", "vs", "better", "distinction"])

    # City detection (use word boundaries and ignore "london stock exchange")
    cities = {
        "riyadh": [r"\briyadh\b", r"\bal-riyadh\b"],
        "jeddah": [r"\bjeddah\b", r"\bjiddah\b"],
        "dubai": [r"\bdubai\b"],
        "muscat": [r"\bmuscat\b"],
        "doha": [r"\bdoha\b", r"\blusail\b", r"\bsimaisma\b"],
        "london": [r"\bmayfair\b", r"\bkensington\b"],
        "benahavis": [r"\bbenahav[íi]s\b", r"\bmarbella\b", r"\bcortesin\b"],
        "dammam": [r"\bdammam\b"],
        "khobar": [r"\bkhobar\b", r"\bal-khobar\b"],
        "makkah": [r"\bmakkah\b", r"\bmecca\b"],
        "madinah": [r"\bmadinah\b", r"\bmedina\b"]
    }

    # Only treat "london" as a city if not referring to "london stock exchange"
    if re.search(r"\blondon\b", q) and not re.search(r"\blondon stock exchange\b", q):
        cities["london"].append(r"\blondon\b")

    detected_city = None
    for city_key, patterns in cities.items():
        if any(re.search(pat, q) for pat in patterns):
            detected_city = city_key
            break

    # Purpose detection
    purpose = None
    if any(w in q for w in ["rent", "rental", "tenant", "lease"]):
        purpose = "rent"
    elif any(w in q for w in ["buy", "purchase", "sale", "invest", "off-plan"]):
        purpose = "sale"

    return {
        "platform": platform,
        "city": detected_city,
        "purpose": purpose,
        "is_comparison": is_comparison
    }


def lexical_score(query_tokens: set[str], text: str) -> float:
    t_lower = text.lower()
    score = 0.0
    for tok in query_tokens:
        if len(tok) < 3:
            continue
        count = t_lower.count(tok)
        if count > 0:
            score += 1.0 + (0.3 * min(count, 5))
    return score


def retrieve_context(
    query: str,
    platform: str | None = None,
    city: str | None = None,
    purpose: str | None = None,
    limit: int = 6
) -> dict[str, Any]:
    """Retrieve top relevant chunks using hybrid vector + lexical search."""
    intent = detect_intent(query)
    effective_platform = platform or intent["platform"]
    effective_city = city or intent["city"]
    effective_purpose = purpose or intent["purpose"]

    # 1. Vector Search via Qdrant
    vector_results = []
    try:
        q_vec = embed_query(query)
        vector_results = search_vector_store(
            query_vector=q_vec,
            limit=limit * 2,
            platform=effective_platform,
            city=city,
            purpose=purpose
        )
    except Exception as e:
        print(f"[Retriever] Vector search fallback: {e}")

    # 2. Lexical scoring over local chunks
    all_chunks = get_all_chunks()
    q_tokens = set(re.findall(r"\w+", query.lower()))
    
    scored_candidates: dict[str, dict] = {}

    # Incorporate vector results
    for r in vector_results:
        payload = r.get("payload") or {}
        cid = payload.get("id")
        if cid:
            scored_candidates[cid] = {
                "chunk": payload,
                "vector_score": float(r.get("score", 0.0)),
                "lexical_score": 0.0,
                "combined_score": float(r.get("score", 0.0)) * 2.0
            }

    # Check metadata filters (only hard-filter platform if detected or requested)
    for ch in all_chunks:
        if effective_platform and ch.get("platform") != effective_platform:
            continue
        if purpose and ch.get("purpose") != purpose and ch.get("purpose") != "info":
            continue
        if city and city not in ("all", "global"):
            # If explicit city filter passed from UI, apply to properties
            if ch.get("kind") == "property" and city.lower() not in (ch.get("city") or ""):
                continue

        lex = lexical_score(q_tokens, ch.get("text", ""))

        # Soft boost if chunk matches detected city
        if intent.get("city") and intent["city"] in (ch.get("city") or ""):
            lex += 2.0

        cid = ch["id"]
        if cid in scored_candidates:
            scored_candidates[cid]["lexical_score"] = lex
            scored_candidates[cid]["combined_score"] += lex * 0.5
        elif lex > 1.0:
            scored_candidates[cid] = {
                "chunk": ch,
                "vector_score": 0.0,
                "lexical_score": lex,
                "combined_score": lex * 0.8
            }

    # Sort candidates by combined score descending
    ranked = sorted(scored_candidates.values(), key=lambda x: x["combined_score"], reverse=True)
    top_items = ranked[:limit]

    # Format context and extract structured sources & properties
    context_blocks = []
    sources = []
    seen_urls = set()
    matched_properties = []
    seen_prop_ids = set()

    for item in top_items:
        ch = item["chunk"]
        context_blocks.append(ch.get("text", ""))
        url = ch.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({
                "title": ch.get("title") or "Verified Property Source",
                "url": url,
                "platform": ch.get("platform"),
                "scraped_at": ch.get("scraped_at")
            })

        # Check for attached structured property data
        prop_data = ch.get("property_data")
        if prop_data and prop_data.get("id") not in seen_prop_ids:
            seen_prop_ids.add(prop_data["id"])
            matched_properties.append(prop_data)

    context_str = "\n\n---\n\n".join(context_blocks)

    return {
        "context": context_str,
        "sources": sources,
        "properties": matched_properties[:4],
        "intent": intent,
        "total_candidates": len(ranked)
    }
