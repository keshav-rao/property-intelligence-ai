from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-lightning:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "property_knowledge"
    cors_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def get_data_dir() -> Path:
    """Resolve data directory consistently across local dev and container environments."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "data",  # <root>/data (local dev)
        Path(__file__).resolve().parent.parent / "data",         # /app/data (container)
        Path("/app/data"),
        Path("data").resolve(),
    ]
    for c in candidates:
        if (c / "processed" / "properties.json").exists():
            return c
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

