"""Property Intelligence AI - FastAPI Application Entrypoint.

DarGlobal × Wasalt AI Assistant Backend.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import LeadRequest
from app.api.chat import router as chat_router
from app.api.properties import router as properties_router, get_properties
from app.api.compare import router as compare_router
from app.api.destinations import DESTINATIONS
from app.rag.vector_store import count_collection

app = FastAPI(
    title="Property Intelligence AI",
    description="Intelligent Conversational Concierge for DarGlobal Luxury Developments and Wasalt Saudi Real Estate.",
    version="1.0.0"
)

# CORS setup
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "*" not in origins:
    origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router)
app.include_router(properties_router)
app.include_router(compare_router)


@app.get("/health")
def health():
    qdrant_count = count_collection()
    props = get_properties()
    return {
        "status": "healthy",
        "service": "Property Intelligence AI",
        "model": settings.openrouter_model,
        "qdrant_collection": settings.qdrant_collection,
        "vector_count": qdrant_count,
        "properties_count": len(props)
    }


@app.get("/api/destinations")
def list_destinations():
    return list(DESTINATIONS.values())


@app.get("/api/stats")
def dataset_stats():
    props = get_properties()
    dg_props = [p for p in props if p.get("platform") == "darglobal"]
    wasalt_props = [p for p in props if p.get("platform") == "wasalt"]
    cities = list(set(p.get("city") for p in props if p.get("city")))
    return {
        "total_properties": len(props),
        "darglobal_projects": len(dg_props),
        "wasalt_listings": len(wasalt_props),
        "cities_covered": len(cities),
        "cities": sorted(cities),
        "qdrant_indexed_chunks": count_collection()
    }


@app.post("/api/leads")
def capture_lead(lead: LeadRequest):
    if not lead.consent:
        raise HTTPException(status_code=400, detail="Explicit consent is required to register interest.")

    leads_file = Path(__file__).resolve().parent / "data" / "leads.jsonl"
    leads_file.parent.mkdir(parents=True, exist_ok=True)

    record = lead.model_dump()
    record["lead_id"] = str(uuid.uuid4())

    with open(leads_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "status": "received",
        "lead_id": record["lead_id"],
        "message": "Thank you! Your interest has been saved in this educational demo environment."
    }
