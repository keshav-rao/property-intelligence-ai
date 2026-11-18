"""Chat completion API router integrating hybrid RAG and OpenRouter."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas import ChatRequest, ChatResponse
from app.rag.retriever import retrieve_context
from app.llm.client import generate_response
from app.api.destinations import DESTINATIONS

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # 1. Retrieve hybrid context
    retrieved = retrieve_context(
        query=req.message,
        platform=req.platform,
        city=req.city,
        purpose=req.purpose,
        limit=6
    )

    context = retrieved["context"]
    sources = retrieved["sources"]
    properties = retrieved["properties"]
    intent = retrieved["intent"]

    # 2. Query OpenRouter
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
    try:
        answer = await generate_response(
            query=req.message,
            context=context,
            history=history_dicts
        )
    except Exception as e:
        print(f"[Chat API] Error from LLM completion: {e}")
        # Graceful fallback: return verified context
        answer = (
            "Here is the verified information found in our database for your query:\n\n"
            + (context[:1200] if context else "No direct matches found in our indexed database.")
        )

    # 3. Destination recommendations
    dest_keys = []
    platform = intent.get("platform")
    if platform == "darglobal":
        dest_keys.extend(["darglobal_home", "darglobal_projects", "darglobal_investor"])
    elif platform == "wasalt":
        city = intent.get("city")
        if city == "riyadh":
            dest_keys.append("wasalt_riyadh_rent")
        elif city == "jeddah":
            dest_keys.append("wasalt_jeddah_rent")
        else:
            dest_keys.append("wasalt_home")
        dest_keys.append("wasalt_business")
    else:
        dest_keys.extend(["darglobal_home", "wasalt_home"])

    recommended_destinations = [
        DESTINATIONS[k] for k in dest_keys if k in DESTINATIONS
    ]

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        intent=intent,
        sources=sources,
        properties=properties,
        destinations=recommended_destinations,
        model=settings.openrouter_model
    )
