"""FastAPI app."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from dataclasses import asdict

from pkh.adapters import get_adapter
from pkh.api.auth import get_current_role, require_permission
from pkh.config.settings import get_settings
from pkh.governance.audit import AuditLog
from pkh.services.ingest import (
    IngestOutcome,
    ingest_source,
)
from pkh.services.query import run_query_pipeline
from pkh.services.runtime import SharedStore
from pkh.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Singleton store per fix-plan 1.6 (Round 2: shared implementation in
# pkh.services.runtime — previously duplicated with cli/main.py)
_shared_store = SharedStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _store = _shared_store.get()
    yield
    # Shutdown: dispose engines/clients (SQLite engine, Chroma client) — trước
    # đây store sống sót qua shutdown, giữ file handles + Chroma client mở.
    _shared_store.close()


app = FastAPI(
    title="PKH API", version="0.1.0", description="Project Knowledge Harness API", lifespan=lifespan
)


def get_store() -> KnowledgeStore:
    return _shared_store.get()


_ALLOWED_SCHEMES = {"git", "confluence", "jira", "document", "file", "http", "https"}


def _validate_single_source(v: str | None) -> str | None:
    if v is None:
        return v
    # Path traversal and sensitive absolute path checks are handled in the
    # ingest endpoint with HTTP 400 (fix-plan 1.7). Here we only validate
    # scheme whitelist and basic git path presence to avoid 422 vs 400 confusion.
    if "://" in v:
        scheme = v.split("://", 1)[0]
        if scheme not in _ALLOWED_SCHEMES:
            raise ValueError(f"unsupported scheme: {scheme}")
        if scheme == "git":
            path = v[6:]
            if not path:
                raise ValueError("git source requires path")
    return v


class IngestRequest(BaseModel):
    source: str | None = None
    sources: list[str] | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str | None) -> str | None:
        return _validate_single_source(v)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        validated: list[str] = []
        for item in v:
            validated.append(_validate_single_source(item))  # type: ignore[arg-type]
        return validated


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    strategy: str | None = None
    provider: str | None = None
    model: str | None = None


class ContextRequest(BaseModel):
    query: str
    top_k: int = 5
    provider: str | None = None


@app.get("/health")
async def health():
    store = get_store()
    hc = await store.health_check()
    return {"status": "ok", "components": hc}


@app.post("/ingest")
async def ingest(req: IngestRequest, role: str = Depends(require_permission("ingest"))):
    # defense in depth: explicit traversal check returning 400 (Pydantic gives 422)
    for src in req.sources or ([req.source] if req.source else []):
        if ".." in src:
            raise HTTPException(status_code=400, detail="path traversal detected")
        if src.startswith("git://"):
            path = src[6:]
            if ".." in Path(path).parts:
                raise HTTPException(status_code=400, detail="path traversal detected")
            try:
                p = Path(path)
                if p.is_absolute():
                    # block sensitive prefixes before resolve (macOS /etc -> /private/etc)
                    blocked_strs = ["/etc", "/proc", "/sys", "/root", "/private/etc"]
                    for bs in blocked_strs:
                        if str(p).startswith(bs):
                            raise HTTPException(status_code=400, detail=f"blocked path: {p}")
                    rp = p.resolve()
                    blocked_paths = [
                        Path("/etc"),
                        Path("/proc"),
                        Path("/sys"),
                        Path("/private/etc"),
                        Path("/root"),
                    ]
                    for b in blocked_paths:
                        try:
                            if rp.is_relative_to(b):
                                raise HTTPException(status_code=400, detail=f"blocked path: {rp}")
                        except AttributeError:
                            if str(rp).startswith(str(b)):
                                raise HTTPException(
                                    status_code=400, detail=f"blocked path: {rp}"
                                ) from None
                    for bs in blocked_strs:
                        if str(rp).startswith(bs):
                            raise HTTPException(status_code=400, detail=f"blocked path: {rp}")
            except HTTPException:
                raise
            except Exception as e:  # defensive: never let a bad path crash validation
                logger.warning(f"source path check skipped for {src}: {e}")
    settings = get_settings()
    sources = req.sources or ([req.source] if req.source else [])
    if not sources:
        # default to local docs
        sources = ["git://./"]
    store = get_store()
    outcomes: list[IngestOutcome] = []
    for src in sources:
        outcomes.append(await ingest_source(store, src, settings, reason="ingest"))
    ingested_count = sum(o.kos_extracted for o in outcomes)
    audit = AuditLog()
    # Blocking disk I/O trong async handler block event loop — wrap to_thread.
    await asyncio.to_thread(
        audit.log,
        "ingest",
        actor=role,
        resource=",".join(sources),
        details={"count": ingested_count, "failed": sum(1 for o in outcomes if not o.ok)},
    )
    return {
        "ingested": ingested_count,
        "sources": sources,
        "results": [asdict(o) for o in outcomes],
    }


@app.get("/ingest/status")
async def ingest_status():
    store = get_store()
    hc = await store.health_check()
    return hc


@app.post("/query")
async def query(req: QueryRequest, role: str = Depends(require_permission("query"))):
    store = get_store()
    package, search_stats, intent = await run_query_pipeline(store, req.query, top_k=req.top_k)

    # format answer via adapter (custom provider supported; key stays server-side)
    from pkh.utils.exceptions import AdapterError, ConfigurationError

    settings = get_settings()
    try:
        adapter = get_adapter(
            req.provider or settings.adapters.default,
            model=req.model,
        )
        answer = await adapter.complete(package)
    except ConfigurationError as e:
        # str(e) của AdapterError/ConfigurationError nhúng upstream URL + status
        # + ≤500 ký tự response body — KHÔNG trả client; chỉ log server-side.
        logger.warning(f"adapter configuration error: {e}")
        raise HTTPException(status_code=400, detail="LLM provider is not configured correctly") from e
    except AdapterError as e:
        logger.error(f"adapter error: {e}")
        raise HTTPException(status_code=502, detail="Upstream LLM provider failed") from e

    audit = AuditLog()
    await asyncio.to_thread(
        audit.log,
        "query",
        actor=role,
        resource=req.query,
        details={"intent": intent.value, "top_k": req.top_k},
    )

    return {
        "query": req.query,
        "intent": intent.value,
        "answer": answer,
        "context": package.model_dump(mode="json"),
        "latency_ms": search_stats.latency_ms,
    }


@app.post("/context")
async def context(req: ContextRequest, role: str = Depends(require_permission("context"))):
    store = get_store()
    package, _, _ = await run_query_pipeline(store, req.query, top_k=req.top_k)
    return package.model_dump(mode="json")


@app.get("/providers")
async def providers():
    """List configured LLM providers (secrets redacted)."""
    settings = get_settings()
    out: dict[str, dict] = {}
    for name, p in settings.adapters.providers.items():
        out[name] = {
            "base_url": p.base_url,
            "model": p.model,
            "embedding_model": p.embedding_model,
            "has_api_key": bool(p.api_key or os.getenv("OPENAI_API_KEY")),
            "timeout_seconds": p.timeout_seconds,
        }
    if settings.adapters.custom_base_url or settings.adapters.custom_model:
        out.setdefault(
            "custom",
            {
                "base_url": settings.adapters.custom_base_url,
                "model": settings.adapters.custom_model,
                "embedding_model": settings.adapters.custom_embedding_model,
                "has_api_key": bool(
                    settings.adapters.custom_api_key or os.getenv("OPENAI_API_KEY")
                ),
                "timeout_seconds": 60.0,
            },
        )
    return {"default": settings.adapters.default, "providers": out}


@app.get("/knowledge/{id}")
async def get_knowledge(id: str):
    store = get_store()
    ko = await store.get(id)
    if not ko:
        raise HTTPException(status_code=404, detail="not found")
    return ko.model_dump(mode="json")


@app.get("/graph/explore")
async def graph_explore(entity_id: str, depth: int = 2):
    store = get_store()
    depth = max(1, min(int(depth), 5))
    # graph load/traverse là blocking disk I/O — off-thread (block event loop
    # khi graph.json lớn).
    neighbors = await asyncio.to_thread(
        lambda: store.graph.get_neighbors(entity_id, max_depth=depth)
    )
    return {"entity_id": entity_id, "neighbors": neighbors[:100], "depth": depth}


@app.get("/sources/status")
async def sources_status():
    settings = get_settings()
    return {"sources": settings.sources.model_dump()}


@app.get("/audit")
async def audit_list(limit: int = 50, role: str = Depends(get_current_role)):
    if role not in ("ADMIN", "ARCHITECT"):
        raise HTTPException(status_code=403, detail="audit requires ADMIN/ARCHITECT")
    audit = AuditLog()
    # Đọc toàn bộ log file (≤10MB) + verify chain là blocking I/O — off-thread.
    entries, verified = await asyncio.to_thread(
        lambda: (audit.list(limit), audit.verify_chain())
    )
    return {"entries": entries, "verified": verified}
