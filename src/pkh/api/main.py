"""FastAPI app."""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from pkh.adapters import get_adapter
from pkh.api.auth import get_current_role
from pkh.config.settings import get_settings
from pkh.engines.context_delivery.assembler import ContextAssembler
from pkh.engines.context_delivery.compressor import compress
from pkh.engines.context_delivery.models import SearchStats
from pkh.engines.context_delivery.validator import ContextValidator
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.engines.retrieval.intent import QueryPlanner, classify_intent
from pkh.engines.retrieval.reranker import deduplicate, rerank
from pkh.engines.retrieval.retriever import HybridRetriever
from pkh.governance.audit import AuditLog
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="PKH API", version="0.1.0", description="Project Knowledge Harness API")


def get_store() -> KnowledgeStore:
    s = get_settings()
    return KnowledgeStore(
        metadata_path=s.storage.metadata.sqlite_path,
        vector_path=s.storage.vector.path,
        graph_path=s.storage.graph.persist_path,
    )


class IngestRequest(BaseModel):
    source: str | None = None
    sources: list[str] | None = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    strategy: str | None = None


class ContextRequest(BaseModel):
    query: str
    top_k: int = 5


@app.get("/health")
async def health():
    store = get_store()
    hc = await store.health_check()
    return {"status": "ok", "components": hc}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    settings = get_settings()
    sources = req.sources or ([req.source] if req.source else [])
    if not sources:
        # default to local docs
        sources = ["git://./"]
    store = get_store()
    all_kos = []
    for src in sources:
        # parse source url
        if src.startswith("git://"):
            path = src[6:]
            conn = GitConnector(repo_url=path)
            mgr = SyncManager([conn])
            items = await mgr.collect_all()
        else:
            # treat as git local
            conn = GitConnector(repo_url=src)
            mgr = SyncManager([conn])
            items = await mgr.collect_all()

        pipeline = ExtractionPipeline(llm_enabled=settings.extraction.llm_enabled)
        kos, stats = await pipeline.run(items)
        # set ACTIVE lifecycle after validation pass
        for ko in kos:
            ko.lifecycle_state = ko.lifecycle_state  # keep as is, but ensure ACTIVE for query
            # simple: move DISCOVERED->EXTRACTED->VALIDATING->ACTIVE
            from pkh.models.knowledge import LifecycleState

            if ko.lifecycle_state.value == "DISCOVERED":
                ko.lifecycle_state = LifecycleState.ACTIVE
            elif ko.lifecycle_state.value == "EXTRACTED":
                ko.lifecycle_state = LifecycleState.ACTIVE
        await store.save(kos)
        all_kos.extend(kos)

    audit = AuditLog()
    audit.log("ingest", resource=",".join(sources), details={"count": len(all_kos)})
    return {"ingested": len(all_kos), "sources": sources}


@app.get("/ingest/status")
async def ingest_status():
    store = get_store()
    hc = await store.health_check()
    return hc


@app.post("/query")
async def query(req: QueryRequest):
    store = get_store()
    intent = classify_intent(req.query)
    planner = QueryPlanner()
    sub_queries = planner.plan(req.query, intent)
    retriever = HybridRetriever(store)
    all_fused: list[tuple] = []
    stats_total: dict[str, int] = {}
    start = time.time()
    for sq in sub_queries:
        fused, stats = await retriever.retrieve(sq, top_k=req.top_k)
        all_fused.extend(fused)
        for k, v in stats.items():
            stats_total[k] = stats_total.get(k, 0) + v

    # deduplicate and rerank
    all_fused = deduplicate(all_fused)
    all_fused = rerank(all_fused)

    # filter ACTIVE etc
    # only keep ACTIVE/UPDATED by default
    active = [
        p for p in all_fused if p[0].lifecycle_state.value in ("ACTIVE", "UPDATED", "EXTRACTED")
    ]
    if not active:
        active = all_fused

    # assemble context
    assembler = ContextAssembler(store)
    search_stats = SearchStats(
        vector_results=stats_total.get("vector", 0),
        keyword_results=stats_total.get("keyword", 0),
        graph_results=stats_total.get("graph", 0),
        total_before_dedup=len(all_fused),
        total_after_dedup=len(active),
        strategies_used=list(stats_total.keys()),
        latency_ms=(time.time() - start) * 1000,
    )
    package = await assembler.assemble(
        req.query, active[: req.top_k], intent=intent, search_stats=search_stats
    )
    package = compress(package)
    validator = ContextValidator()
    vr = validator.validate(package)
    if vr.warnings:
        package.warnings.extend([w for w in vr.warnings if w not in package.warnings])

    # format answer via adapter
    settings = get_settings()
    adapter = get_adapter(settings.adapters.default)
    answer = await adapter.complete(package)

    audit = AuditLog()
    audit.log("query", resource=req.query, details={"intent": intent.value, "top_k": req.top_k})

    return {
        "query": req.query,
        "intent": intent.value,
        "answer": answer,
        "context": package.model_dump(mode="json"),
        "latency_ms": search_stats.latency_ms,
    }


@app.post("/context")
async def context(req: ContextRequest):
    store = get_store()
    intent = classify_intent(req.query)
    retriever = HybridRetriever(store)
    fused, stats = await retriever.retrieve(req.query, top_k=req.top_k)
    fused = deduplicate(fused)
    fused = rerank(fused)
    assembler = ContextAssembler(store)
    search_stats = SearchStats(
        vector_results=stats.get("vector", 0),
        keyword_results=stats.get("keyword", 0),
        graph_results=stats.get("graph", 0),
        total_before_dedup=len(fused),
        total_after_dedup=len(fused),
        strategies_used=list(stats.keys()),
    )
    package = await assembler.assemble(
        req.query, fused[: req.top_k], intent=intent, search_stats=search_stats
    )
    package = compress(package)
    return package.model_dump(mode="json")


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
    neighbors = store.graph.get_neighbors(entity_id, max_depth=depth)
    return {"entity_id": entity_id, "neighbors": neighbors, "depth": depth}


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
