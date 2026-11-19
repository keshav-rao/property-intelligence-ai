"""Property Intelligence AI: FastAPI application.

Endpoints
  POST /api/chat             one structured reply (answer + cards + sources + actions + quick replies)
  POST /api/chat/stream      same reply as Server-Sent Events: `meta`, then `token`s, then `done`
  POST /api/search           filter the catalogue directly (no LLM)
  POST /api/recommendations  ranked recommendations for a set of preferences
  POST /api/compare          side-by-side comparison data for 2-3 items
  GET  /api/destinations     approved official links
  POST /api/leads            enquiry with explicit consent (never sent to the LLM)
  GET  /api/health, /api/stats
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import dialogue, llm, rag
from app.catalog import by_id, card, load_catalog, stats
from app.config import settings
from app.destinations import DESTINATIONS, darglobal_country, wasalt_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="Property Intelligence AI — DarGlobal × Wasalt", version="2.0.0")
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


@app.on_event("startup")
async def startup() -> None:
    load_catalog()
    # Build/load the vector index without blocking the first requests (BM25 works meanwhile).
    asyncio.get_running_loop().run_in_executor(None, rag.init)


# ----------------------------------------------------------------------------- schemas


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(None, max_length=64)
    compare_ids: list[str] | None = Field(None, max_length=3)


class SearchIn(BaseModel):
    platform: str | None = Field(None, pattern="^(darglobal|wasalt)$")
    purpose: str | None = Field(None, pattern="^(sale|rent)$")
    city: str | None = None
    country: str | None = None
    property_type: str | None = None
    bedrooms: int | None = Field(None, ge=0, le=20)
    budget_min: float | None = Field(None, ge=0)
    budget_max: float | None = Field(None, ge=0)
    brand: str | None = None
    limit: int = Field(12, ge=1, le=50)


class CompareIn(BaseModel):
    ids: list[str] = Field(..., min_length=2, max_length=3)


class LeadIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str | None = Field(None, max_length=120)
    phone: str | None = Field(None, max_length=30)
    platform: str = Field("darglobal", pattern="^(darglobal|wasalt)$")
    interest: str | None = Field(None, max_length=300)
    project_id: str | None = Field(None, max_length=120)
    preferred_contact: str | None = Field(None, pattern="^(email|phone|whatsapp)$")
    message: str | None = Field(None, max_length=600)
    consent: bool = False
    session_id: str | None = Field(None, max_length=64)


# ----------------------------------------------------------------------------- chat


async def _phrase(msgs: list[dict] | None, fallback: str) -> tuple[str, str | None]:
    if not msgs:
        return fallback, None
    text, model = await llm.complete(msgs, max_tokens=420)
    return (text, model) if text else (fallback, None)


@app.post("/api/chat")
async def chat(body: ChatIn):
    reply, msgs, session = dialogue.handle(body.message, body.session_id, body.compare_ids)
    answer, model = await _phrase(msgs, reply["answer"])
    reply.update(answer=answer, llm=model, grounded=bool(model))
    dialogue.remember_answer(session, answer)
    return reply


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(body: ChatIn):
    reply, msgs, session = dialogue.handle(body.message, body.session_id, body.compare_ids)
    fallback = reply["answer"]

    async def gen():
        meta = {k: v for k, v in reply.items() if k != "answer"}
        yield _sse("meta", meta)
        parts, model = [], None
        if msgs:
            try:
                async for tok, m in llm.stream(msgs, max_tokens=420):
                    parts.append(tok)
                    model = m
                    yield _sse("token", {"t": tok})
            except Exception as e:  # never break the chat on a model error
                log.warning("stream failed: %s", e)
        if not parts:
            # deterministic text, sent in a few chunks so the UI animates the same way
            for chunk in re.findall(r"\S+\s*", fallback):
                yield _sse("token", {"t": chunk})
                await asyncio.sleep(0.012)
        answer = "".join(parts) if parts else fallback
        dialogue.remember_answer(session, answer)
        yield _sse("done", {"answer": answer, "llm": model, "grounded": bool(model)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ----------------------------------------------------------------------------- data endpoints


def _filters(q: SearchIn) -> dict:
    from app.nlu import find_city

    f = {k: v for k, v in q.model_dump().items() if v is not None and k != "limit"}
    if f.get("city"):
        f["city"] = find_city(f["city"]) or f["city"].lower()
    return f


@app.post("/api/search")
def search(q: SearchIn):
    f = _filters(q)
    platforms = [f["platform"]] if f.get("platform") else ["wasalt", "darglobal"]
    out = []
    for p in platforms:
        out += dialogue.match(f, p)
    return {"filters": f, "total": len(out), "results": [card(x) for x in out[: q.limit]]}


@app.post("/api/recommendations")
def recommendations(q: SearchIn):
    f = _filters(q)
    platform = f.get("platform") or dialogue.platform_for(f) or "wasalt"
    items, note = dialogue.recommend(f, platform)
    actions = ([wasalt_search(f.get("purpose"), f.get("city"), f.get("property_type"))] if platform == "wasalt"
               else [darglobal_country(f.get("country"), f.get("city"))])
    return {"filters": f, "platform": platform, "note": note, "total": len(items),
            "results": [card(x) for x in items[: q.limit]], "actions": actions}


@app.post("/api/compare")
def compare(body: CompareIn):
    reply, _, _ = dialogue.handle("compare", None, body.ids)
    if not reply.get("ui"):
        raise HTTPException(404, "Need at least two known item ids.")
    return reply["ui"]


@app.get("/api/destinations")
def destinations():
    return list(DESTINATIONS.values())


@app.get("/api/items/{item_id}")
def item(item_id: str):
    x = by_id(item_id)
    if not x:
        raise HTTPException(404, "Unknown item")
    return dict(card(x), description=x["description"])


# ----------------------------------------------------------------------------- leads

EMAIL_OK = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PHONE_OK = re.compile(r"^\+?[\d\s-]{8,20}$")


@app.post("/api/leads")
def leads(body: LeadIn):
    if not body.consent:
        raise HTTPException(400, "Please tick the consent box so we can share your details with an advisor.")
    if not body.email and not body.phone:
        raise HTTPException(400, "Please add an email address or a phone number.")
    if body.email and not EMAIL_OK.match(body.email.strip()):
        raise HTTPException(400, "That email address doesn't look right.")
    if body.phone and not PHONE_OK.match(body.phone.strip()):
        raise HTTPException(400, "That phone number doesn't look right. Include the country code, e.g. +966.")
    ref = "PI-" + uuid.uuid4().hex[:8].upper()
    record = body.model_dump()
    record.update(reference=ref, received_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  consent_text="I agree to be contacted about this enquiry.")
    path = settings.data_path / "leads"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "leads.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    project = by_id(body.project_id) if body.project_id else None
    official = (project["url"] if project else
                DESTINATIONS["wasalt_home"]["url"] if body.platform == "wasalt" else DESTINATIONS["darglobal_contact"]["url"])
    return {"status": "received", "reference": ref, "official_url": official,
            "message": ("Thank you. Your enquiry is saved (reference " + ref + "). This is a demo, so it is stored here and "
                        "not sent to DarGlobal or Wasalt. To reach their teams directly, use the official link.")}


# ----------------------------------------------------------------------------- health


@app.get("/api/health")
def health():
    return {"status": "ok", "model": settings.openrouter_model, "llm_configured": llm.available(),
            "retrieval": rag.status(), "catalogue": stats()}


@app.get("/api/stats")
def api_stats():
    return stats()
