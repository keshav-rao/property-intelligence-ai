"""Runtime configuration (environment variables / .env)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # LLM (OpenRouter)
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-lightning:free"
    openrouter_fallback_models: str = "google/gemma-4-31b-it:free,nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_s: float = 25.0

    # Vector store. "http://qdrant:6333" for the Docker service, or "local" for an
    # embedded on-disk Qdrant (handy for running without Docker).
    qdrant_url: str = "local"
    qdrant_collection: str = "property_knowledge"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # App
    cors_origins: str = "http://localhost:3000"
    data_dir: str = ""
    session_ttl_minutes: int = 120

    model_config = SettingsConfigDict(env_file=(str(ROOT / ".env"), ".env"), extra="ignore")

    @property
    def data_path(self) -> Path:
        if self.data_dir:
            return Path(self.data_dir)
        for c in (ROOT / "data", Path("/app/data")):
            if c.exists():
                return c
        return ROOT / "data"

    @property
    def models(self) -> list[str]:
        extra = [m.strip() for m in self.openrouter_fallback_models.split(",") if m.strip()]
        return [self.openrouter_model] + [m for m in extra if m != self.openrouter_model]


settings = Settings()
