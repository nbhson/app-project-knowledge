"""FastAPI app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from pkh.adapters import get_adapter
from pkh.api.auth import get_current_role, require_permission
from pkh.config.settings import get_settings
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.confluence_connector import ConfluenceConnector
from pkh.engines.ingestion.document_connector import DocumentConnector
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.jira_connector import JiraConnector
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.governance.audit import AuditLog
from pkh.services.query import run_query_pipeline
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Singleton store per fix-plan 1.6
_store: KnowledgeStore | None = None
_store_key: tuple[str, str, str] | None = None


def _store_key_from_settings() -> tuple[str, str, str]:
    s = get_settings()
    return (
        s.storage.metadata.sqlite_path,
        s.storage.vector.path,
        s.storage.graph.persist_path,
    )


def _create_store() -> KnowledgeStore:
    s = get_settings()
    return KnowledgeStore(
        metadata_path=s.storage.metadata.sqlite_path,
        vector_path=s.storage.vector.path,
        graph_path=s.storage.graph.persist_path,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store, _store_key
    key = _store_key_from_settings()
    _store = _create_store()
    _store_key = key
    yield
    # do not clear _store on shutdown to avoid recreation issues; keep singleton


app = FastAPI(
    title="PKH API", version="0.1.0", description="Project Knowledge Harness API", lifespan=lifespan
)


def get_store() -> KnowledgeStore:
    global _store, _store_key
    key = _store_key_from_settings()
    if _store is None or _store_key != key:
        _store = _create_store()
        _store_key = key
    return _store


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
            except Exception:
                pass
    settings = get_settings()
    sources = req.sources or ([req.source] if req.source else [])
    if not sources:
        # default to local docs
        sources = ["git://./"]
    store = get_store()
    all_kos = []
    for src in sources:
        # parse source url — support all 4 schemes like CLI
        conn: object
        if src.startswith("git://"):
            git_path = src[6:]
            conn = GitConnector(repo_url=git_path)
        elif src.startswith("confluence://"):
            space = src[len("confluence://") :]
            conn = ConfluenceConnector(
                base_url=settings.sources.confluence.url, spaces=[space] if space else []
            )
        elif src.startswith("jira://"):
            proj = src[len("jira://") :]
            conn = JiraConnector(
                base_url=settings.sources.jira.url, projects=[proj] if proj else []
            )
        elif src.startswith("document://"):
            doc_path = src[len("document://") :]
            conn = DocumentConnector(paths=[doc_path])
        else:
            # treat as git local
            conn = GitConnector(repo_url=src)
        mgr = SyncManager([conn])  # type: ignore[list-item]
        items = await mgr.collect_all()

        pipeline = ExtractionPipeline(
            llm_enabled=settings.extraction.llm_enabled,
            llm_adapter=(
                get_adapter(settings.extraction.llm_adapter)
                if settings.extraction.llm_enabled
                else None
            ),
            budget_tokens=settings.extraction.budget_per_run_tokens,
            batch_size=settings.extraction.batch_size,
        )
        kos, stats = await pipeline.run(items)
        # Transition via state machine to ACTIVE for querying
        from pkh.models.knowledge import LifecycleState
        from pkh.models.lifecycle import transition as lifecycle_transition

        transitioned = []
        for ko in kos:
            cur = ko.lifecycle_state
            try:
                if cur == LifecycleState.DISCOVERED:
                    ko = lifecycle_transition(ko, LifecycleState.EXTRACTED, reason="ingest")
                    ko = lifecycle_transition(ko, LifecycleState.VALIDATING, reason="ingest")
                    ko = lifecycle_transition(ko, LifecycleState.ACTIVE, reason="ingest")
                elif cur == LifecycleState.EXTRACTED:
                    ko = lifecycle_transition(ko, LifecycleState.VALIDATING, reason="ingest")
                    ko = lifecycle_transition(ko, LifecycleState.ACTIVE, reason="ingest")
                elif cur == LifecycleState.VALIDATING:
                    ko = lifecycle_transition(ko, LifecycleState.ACTIVE, reason="ingest")
            except Exception as e:
                # do not cheat state-machine: keep original state and log
                logger.warning(f"Lifecycle transition failed for {ko.id}: {e}")
            transitioned.append(ko)
        kos = transitioned
        await store.save(kos)
        all_kos.extend(kos)

    audit = AuditLog()
    audit.log("ingest", actor=role, resource=",".join(sources), details={"count": len(all_kos)})
    return {"ingested": len(all_kos), "sources": sources}


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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AdapterError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    audit = AuditLog()
    audit.log(
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
            "has_api_key": bool(p.api_key or __import__("os").getenv("OPENAI_API_KEY")),
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
                    settings.adapters.custom_api_key or __import__("os").getenv("OPENAI_API_KEY")
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
    neighbors = store.graph.get_neighbors(entity_id, max_depth=depth)
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
    return {"entries": audit.list(limit), "verified": audit.verify_chain()}
