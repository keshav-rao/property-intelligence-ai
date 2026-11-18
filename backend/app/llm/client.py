"""OpenRouter LLM completion service with retry handling and active free model fallback."""
from __future__ import annotations

import asyncio
import os
import re
import httpx
from app.config import settings
from app.rag.prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

ACTIVE_FREE_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "liquid/lfm-3-1.7b:free",
    "baidu/ernie-5.5-flash-preview:free"
]


def clean_think_tags(text: str) -> str:
    """Strip out internal reasoning tokens if model outputs raw <think> tags."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


async def generate_response(
    query: str,
    context: str,
    history: list[dict] | None = None,
    temperature: float = 0.2
) -> str:
    """Generate completion via OpenRouter with automatic fallback on failure."""
    if history is None:
        history = []

    history_str = "\n".join(f"{m.get('role', 'user').title()}: {m.get('content', '')}" for m in history[-6:])
    if not history_str:
        history_str = "None"

    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context or "No specific context available.",
        query=query,
        history=history_str
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    models_to_try = [settings.openrouter_model] + [m for m in ACTIVE_FREE_MODELS if m != settings.openrouter_model]

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://property-intelligence-ai.local",
        "X-Title": "Property Intelligence AI"
    }

    async with httpx.AsyncClient(timeout=35.0) as client:
        for model in models_to_try:
            for attempt in range(2):
                try:
                    payload = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 1200
                    }
                    resp = await client.post(
                        f"{settings.openrouter_base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message") or {}
                            content = msg.get("content")
                            if content:
                                cleaned = clean_think_tags(content)
                                if cleaned:
                                    return cleaned
                            # Fallback if reasoning model put text in reasoning
                            reasoning = msg.get("reasoning")
                            if reasoning:
                                cleaned = clean_think_tags(reasoning)
                                if cleaned and len(cleaned) > 20:
                                    return cleaned
                    elif resp.status_code in (429, 502, 503):
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    else:
                        break
                except Exception as e:
                    await asyncio.sleep(0.5)

    # If all models failed or offline, return a structured fallback based directly on retrieved context
    if context:
        return (
            "Based on the verified property database, here is the relevant context retrieved for your inquiry:\n\n"
            + context[:1200]
            + "\n\n*(Note: No records outside the verified dataset are present. If you asked about a property, partnership, or location not listed, it is not available in the collected dataset.)*"
        )
    return "I am currently unable to reach the AI model provider, and no matching records are available in the verified dataset."
