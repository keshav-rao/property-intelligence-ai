"""Hybrid retrieval over the knowledge documents and the property catalogue.

* Dense: BAAI/bge-small-en-v1.5 embeddings (fastembed, ONNX, CPU) stored in Qdrant.
  Qdrant runs as a Docker service in production; locally it can run embedded
  (QDRANT_URL=local), so the app also works without Docker.
* Sparse: a small BM25 scorer over the same texts, for exact names such as "DG1" or
  "Les Vagues" that embeddings can blur.
* Metadata filter: platform (darglobal / wasalt) when the conversation knows it.

The index is rebuilt automatically when the document set changes (content hash).
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import threading
from collections import Counter

from app.catalog import load_catalog
from app.config import settings
from app.knowledge import KNOWLEDGE

log = logging.getLogger("rag")
_lock = threading.Lock()
_state: dict = {"ready": False, "client": None, "embedder": None, "docs": [], "bm25": None, "error": None}

TOKEN = re.compile(r"[a-z0-9]+")
STOP = set("the a an and or of in on to for with by at is are be this that from as it its your you i me my we our "
           "what which who how can do does any some show find tell about please".split())


def _tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def build_documents() -> list[dict]:
    docs = []
    for k in KNOWLEDGE:
        docs.append({"id": k["id"], "kind": "knowledge", "platform": k["platform"], "title": k["title"],
                     "url": k["url"], "text": f"{k['title']}. {k['text']}"})
    for x in load_catalog():
        if x["platform"] == "darglobal":
            text = (f"{x['title']} by DarGlobal. {x['type_label']} in {x.get('district') + ', ' if x.get('district') else ''}"
                    f"{x['city']}, {x['country']}. Brand partner: {x.get('brand') or 'none'}. "
                    f"Bedrooms: {x.get('bedrooms_label') or 'not stated'}. Sizes: {x.get('area_label') or 'not stated'}. "
                    f"Completion: {x.get('completion') or 'not stated'}. Status: {x.get('status')}. {x['description']}")
        else:
            text = f"{x['title']} on Wasalt. {x['description']} Price: {x['price_label']}."
        docs.append({"id": x["id"], "kind": "property", "platform": x["platform"], "title": x["title"],
                     "url": x["url"], "text": text})
    return docs


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(_tokens(t)) for t in texts]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(len(self.len), 1)
        df = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(texts)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def scores(self, query: str) -> list[float]:
        q = _tokens(query)
        out = []
        for c, ln in zip(self.tf, self.len):
            s = 0.0
            for w in q:
                if w in c:
                    f = c[w]
                    s += self.idf.get(w, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / self.avg))
            out.append(s)
        return out


def _client():
    from qdrant_client import QdrantClient

    if settings.qdrant_url in ("local", ""):
        path = settings.data_path / "qdrant_local"
        path.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(path))
    if settings.qdrant_url == ":memory:":
        return QdrantClient(":memory:")
    return QdrantClient(url=settings.qdrant_url, timeout=20)


def init() -> None:
    """Load the embedder, (re)build the collection if needed. Safe to call twice."""
    with _lock:
        if _state["ready"]:
            return
        docs = build_documents()
        _state["docs"] = docs
        _state["bm25"] = BM25([d["text"] for d in docs])

        # Use lightweight BM25 retrieval on memory-constrained hosting.
        if os.getenv("DISABLE_DENSE_RETRIEVAL", "").lower() in ("1", "true", "yes"):
            log.warning("Dense retrieval disabled. Using BM25 only.")
            _state.update(
                ready=True,
                client=None,
                embedder=None,
                error="Dense retrieval disabled by configuration",
            )
            return

        try:
            from fastembed import TextEmbedding
            from qdrant_client import models

            embedder = TextEmbedding(settings.embedding_model, cache_dir=os.getenv("FASTEMBED_CACHE_PATH") or None)
            client = _client()
            digest = hashlib.sha1("".join(d["id"] + d["text"] for d in docs).encode()).hexdigest()[:16]
            name = settings.qdrant_collection
            rebuild = True
            if client.collection_exists(name):
                points = client.count(name).count
                stored = client.retrieve(name, ids=[0], with_payload=True)
                if points == len(docs) and stored and stored[0].payload.get("digest") == digest:
                    rebuild = False
            if rebuild:
                vectors = list(embedder.passage_embed([d["text"] for d in docs]))
                if client.collection_exists(name):
                    client.delete_collection(name)
                client.create_collection(name, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE))
                client.upsert(name, points=[
                    models.PointStruct(id=i, vector=list(map(float, v)),
                                       payload={"doc_id": d["id"], "platform": d["platform"], "kind": d["kind"], "digest": digest})
                    for i, (d, v) in enumerate(zip(docs, vectors))
                ])
                log.info("indexed %d documents into %s", len(docs), name)
            _state.update(client=client, embedder=embedder, ready=True, error=None)
        except Exception as e:  # dense search unavailable: BM25 still works
            log.exception("vector index unavailable: %s", e)
            _state.update(ready=True, error=str(e))


def search(query: str, platform: str | None = None, kind: str | None = None, k: int = 6) -> list[dict]:
    if not _state["ready"]:
        init()
    docs = _state["docs"]
    idx = [i for i, d in enumerate(docs) if (not platform or d["platform"] == platform) and (not kind or d["kind"] == kind)]
    if not idx:
        return []
    sparse = _state["bm25"].scores(query)
    smax = max((sparse[i] for i in idx), default=0) or 1.0
    dense: dict[int, float] = {}
    if _state.get("client") is not None:
        try:
            from qdrant_client import models

            vec = next(iter(_state["embedder"].query_embed([query])))
            must = []
            if platform:
                must.append(models.FieldCondition(key="platform", match=models.MatchValue(value=platform)))
            if kind:
                must.append(models.FieldCondition(key="kind", match=models.MatchValue(value=kind)))
            hits = _state["client"].query_points(settings.qdrant_collection, query=list(map(float, vec)), limit=max(k * 4, 20),
                                                 query_filter=models.Filter(must=must) if must else None).points
            dense = {h.id: h.score for h in hits}
        except Exception as e:
            log.warning("dense search failed: %s", e)
    q = query.lower()
    scored = []
    for i in idx:
        d = docs[i]
        s = 0.65 * dense.get(i, 0.0) + 0.35 * (sparse[i] / smax)
        title = d["title"].lower().split(",")[0]
        if len(title) > 3 and title in q:  # exact project name mentioned
            s += 0.5
        scored.append((s, d))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [dict(d, score=round(s, 4)) for s, d in scored[:k] if s > 0.05]


def status() -> dict:
    return {"ready": _state["ready"], "documents": len(_state["docs"]), "dense": _state.get("client") is not None,
            "error": _state.get("error"), "backend": "qdrant-local" if settings.qdrant_url in ("local", "") else settings.qdrant_url}
