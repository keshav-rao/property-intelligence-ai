"""OpenRouter client: one call for a full answer, one for a token stream.

The default model (nvidia/nemotron-3.5-lightning:free) is a reasoning model; with
reasoning switched off it answers in about 1-2 seconds instead of spending its token
budget on hidden thinking. If the primary model fails or is rate-limited, the next free
model in OPENROUTER_FALLBACK_MODELS is tried. Callers always get a deterministic
fallback when every model fails, so the chat never breaks.

Privacy: OpenRouter's free endpoints may log prompts, so callers must never put a
user's name, email or phone number in `messages` (lead details stay in the backend).
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.config import settings

log = logging.getLogger("llm")

HEADERS_EXTRA = {"HTTP-Referer": "https://github.com/property-intelligence-ai", "X-Title": "Property Intelligence AI"}


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json", **HEADERS_EXTRA}


def _payload(model: str, messages: list[dict], max_tokens: int, temperature: float, stream: bool) -> dict:
    return {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
        "reasoning": {"enabled": False},
    }


def available() -> bool:
    return bool(settings.openrouter_api_key)


async def complete(messages: list[dict], max_tokens: int = 500, temperature: float = 0.3) -> tuple[str | None, str | None]:
    """Return (text, model) or (None, None) when no model could answer."""
    if not available():
        return None, None
    async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as client:
        for model in settings.models:
            try:
                r = await client.post(f"{settings.openrouter_base_url}/chat/completions", headers=_headers(),
                                      json=_payload(model, messages, max_tokens, temperature, False))
                if r.status_code != 200:
                    log.warning("model %s returned %s: %s", model, r.status_code, r.text[:200])
                    continue
                msg = (r.json().get("choices") or [{}])[0].get("message") or {}
                text = (msg.get("content") or "").strip()
                if text:
                    return text, model
            except Exception as e:  # network error or timeout: try the next model
                log.warning("model %s failed: %s", model, e)
    return None, None


async def stream(messages: list[dict], max_tokens: int = 500, temperature: float = 0.3) -> AsyncIterator[tuple[str, str]]:
    """Yield (token, model). Yields nothing if every model fails before producing text."""
    if not available():
        return
    timeout = httpx.Timeout(settings.llm_timeout_s, read=settings.llm_timeout_s)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in settings.models:
            produced = False
            try:
                async with client.stream("POST", f"{settings.openrouter_base_url}/chat/completions", headers=_headers(),
                                         json=_payload(model, messages, max_tokens, temperature, True)) as r:
                    if r.status_code != 200:
                        log.warning("stream %s returned %s", model, r.status_code)
                        continue
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            delta = json.loads(data)["choices"][0].get("delta") or {}
                        except (ValueError, KeyError, IndexError):
                            continue
                        tok = delta.get("content")
                        if tok:
                            produced = True
                            yield tok, model
                if produced:
                    return
            except Exception as e:
                log.warning("stream %s failed: %s", model, e)
                if produced:  # partial answer already sent; stop rather than restart mid-sentence
                    return
