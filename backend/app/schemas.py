"""Pydantic schemas for request and response validation."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    platform: str | None = None
    city: str | None = None
    purpose: str | None = None


class SourceItem(BaseModel):
    title: str
    url: str
    platform: str
    scraped_at: str | None = None


class PropertyItem(BaseModel):
    id: str
    name: str | None = None
    title: str
    platform: str
    url: str
    city: str
    country: str
    district: str | None = None
    property_type: str
    category: str | None = None
    purpose: str
    price_display: str
    price_numeric: float = 0
    currency: str = "SAR"
    bedrooms: Any | None = None
    bathrooms: Any | None = None
    area_sqm: Any | None = None
    developer: str | None = None
    brand_partner: str | None = None
    amenities: list[str] = Field(default_factory=list)
    description: str | None = None
    investment_highlights: str | None = None
    scraped_at: str | None = None


class DestinationItem(BaseModel):
    label: str
    url: str
    platform: str
    description: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: dict[str, Any]
    sources: list[SourceItem]
    properties: list[PropertyItem]
    destinations: list[DestinationItem]
    model: str


class CompareRequest(BaseModel):
    property_ids: list[str] = Field(..., min_length=2, max_length=4)


class CompareResponse(BaseModel):
    properties: list[PropertyItem]
    comparison_summary: str


class LeadRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(...)
    phone: str | None = None
    message: str | None = None
    project_of_interest: str | None = None
    consent: bool = False
