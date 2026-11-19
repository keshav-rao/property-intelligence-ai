# Build context: repository root (needs ./data). See docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/models \
    DATA_DIR=/app/data \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so the container starts fast and works offline.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/models')"

COPY backend/app ./app
COPY data/raw/darglobal/projects_live.json ./data/raw/darglobal/projects_live.json
COPY data/raw/wasalt/snapshot.json ./data/raw/wasalt/snapshot.json

RUN useradd -m appuser && mkdir -p /app/data/leads /app/data/qdrant_local && chown -R appuser:appuser /app/data /models
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=3 CMD curl -fs http://localhost:8000/api/health || exit 1
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
