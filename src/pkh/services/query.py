"""Shared query pipeline: classify -> plan -> retrieve -> dedup -> rerank -> assemble.

Used by both FastAPI (api/main.py) and Typer CLI (cli/main.py) to avoid
triple-duplication.
"""

from __future__ import annotations

import time

from pkh.engines.context_delivery.assembler import ContextAssembler
from pkh.engines.context_delivery.compressor import compress
from pkh.engines.context_delivery.models import ContextPackage, SearchStats
from pkh.engines.context_delivery.validator import ContextValidator
from pkh.engines.retrieval.intent import IntentType, QueryPlanner, classify_intent
from pkh.engines.retrieval.reranker import deduplicate, rerank
from pkh.engines.retrieval.retriever import HybridRetriever
from pkh.storage.unified import KnowledgeStore


async def run_query_pipeline(
    store: KnowledgeStore,
    query: str,
    top_k: int = 5,
) -> tuple[ContextPackage, SearchStats, IntentType]:
    intent = classify_intent(query)
    planner = QueryPlanner()
    sub_queries = planner.plan(query, intent)
    retriever = HybridRetriever(store)
    all_fused: list = []
    stats_total: dict[str, int] = {}
    start = time.time()
    for sq in sub_queries:
        fused, stats = await retriever.retrieve_with_intent(sq, intent, top_k=top_k)
        all_fused.extend(fused)
        for k, v in stats.items():
            stats_total[k] = stats_total.get(k, 0) + v

    all_fused = deduplicate(all_fused)
    # rerank with configured weights
    try:
        from pkh.config.settings import get_settings

        rw = get_settings().retrieval.reranker
        all_fused = rerank(
            all_fused,
            confidence_weight=rw.confidence_weight,
            lifecycle_weight=rw.lifecycle_weight,
            recency_weight=rw.recency_weight,
            relevance_weight=rw.relevance_weight,
        )
    except Exception:
        all_fused = rerank(all_fused)

    active = [
        p for p in all_fused if p[0].lifecycle_state.value in ("ACTIVE", "UPDATED", "EXTRACTED")
    ]
    if not active:
        active = all_fused

    search_stats = SearchStats(
        vector_results=stats_total.get("vector", 0),
        keyword_results=stats_total.get("keyword", 0),
        graph_results=stats_total.get("graph", 0),
        total_before_dedup=len(all_fused),
        total_after_dedup=len(active),
        strategies_used=list(stats_total.keys()),
        latency_ms=(time.time() - start) * 1000,
    )
    assembler = ContextAssembler(store)
    package = await assembler.assemble(
        query, active[:top_k], intent=intent, search_stats=search_stats
    )
    package = compress(package)
    validator = ContextValidator()
    vr = validator.validate(package)
    if vr.warnings:
        for w in vr.warnings:
            if w not in package.warnings:
                package.warnings.append(w)
    return package, search_stats, intent
