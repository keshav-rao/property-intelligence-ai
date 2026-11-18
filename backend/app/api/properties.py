"""Properties API router for browsing, filtering, and property details."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query

from app.config import get_data_dir
from app.schemas import PropertyItem

router = APIRouter(prefix="/api/properties", tags=["Properties"])
PROPERTIES_FILE = get_data_dir() / "processed" / "properties.json"

_properties_cache: list[dict] | None = None


def get_properties() -> list[dict]:
    global _properties_cache
    if _properties_cache is not None:
        return _properties_cache
    if PROPERTIES_FILE.exists():
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            _properties_cache = json.load(f)
            return _properties_cache
    return []


@router.get("", response_model=list[PropertyItem])
def list_properties(
    platform: str | None = Query(None, description="Filter by platform: darglobal or wasalt"),
    city: str | None = Query(None, description="Filter by city: riyadh, jeddah, dubai, etc."),
    purpose: str | None = Query(None, description="Filter by purpose: sale or rent"),
    property_type: str | None = Query(None, description="Filter by type: villa, apartment, etc."),
    search: str | None = Query(None, description="Keyword search in title or description"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    items = get_properties()

    if platform:
        p_clean = platform.lower().strip()
        items = [i for i in items if i.get("platform", "").lower() == p_clean]

    if city:
        c_clean = city.lower().strip()
        items = [i for i in items if c_clean in (i.get("city") or "").lower()]

    if purpose:
        purp_clean = purpose.lower().strip()
        items = [i for i in items if i.get("purpose", "").lower() == purp_clean]

    if property_type:
        pt_clean = property_type.lower().strip()
        items = [i for i in items if pt_clean in (i.get("property_type") or "").lower()]

    if search:
        s_clean = search.lower().strip()
        items = [
            i for i in items
            if s_clean in (i.get("title") or "").lower()
            or s_clean in (i.get("description") or "").lower()
            or s_clean in (i.get("developer") or "").lower()
            or s_clean in (i.get("brand_partner") or "").lower()
        ]

    return items[offset:offset + limit]


@router.get("/{property_id}", response_model=PropertyItem)
def get_property(property_id: str):
    items = get_properties()
    for item in items:
        if item.get("id") == property_id:
            return item
    raise HTTPException(status_code=404, detail="Property not found")
