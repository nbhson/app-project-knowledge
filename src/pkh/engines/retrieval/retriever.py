"""Hybrid retriever with RRF fusion."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass

from pkh.engines.retrieval.intent import IntentType
from pkh.models.knowledge import KnowledgeObject
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    strategy: str
    query: str
    results: list[KnowledgeObject]
    scores: list[float]


def rrf_fuse(results: list[RetrievalResult], k: int = 60) -> list[tuple[KnowledgeObject, float]]:
    score_map: dict[str, float] = defaultdict(float)
    obj_map: dict[str, KnowledgeObject] = {}
    for rr in results:
        for rank, (obj, _orig_score) in enumerate(zip(rr.results, rr.scores, strict=True), start=1):
            score_map[obj.id] += 1.0 / (k + rank)
            # keep highest original score object
            if obj.id not in obj_map:
                obj_map[obj.id] = obj
    sorted_ids = sorted(score_map, key=lambda x: score_map[x], reverse=True)
    return [(obj_map[i], score_map[i]) for i in sorted_ids]


class HybridRetriever:
    def __init__(self, store: KnowledgeStore, k: int = 60):
        self.store = store
        self.k = k

    async def _vector_search(self, query: str, top_k: int = 10) -> RetrievalResult:
        try:
            pairs = await self.store.vector.query(query, top_k=top_k)
            objs = [ko for ko, _s in pairs]
            scores = [s for _ko, s in pairs]
            return RetrievalResult(strategy="vector", query=query, results=objs, scores=scores)
        except Exception as e:
            logger.warning(f"vector search failed: {e}")
            return RetrievalResult(strategy="vector", query=query, results=[], scores=[])

    async def _keyword_search(self, query: str, top_k: int = 10) -> RetrievalResult:
        try:
            import re

            # fetch with larger limit to ensure relevant entities are not truncated
            fetch_limit = max(100, top_k * 10)
            objs = self.store.metadata.query(filters={"query": query}, limit=fetch_limit)
            if not objs:
                # tokenize via regex word extraction for robustness (handles punctuation, camelCase)
                tokens = re.findall(r"\w+", query.lower())
                tokens = [t for t in tokens if len(t) > 2]
                # filter common stop words
                stop = {
                    "how",
                    "does",
                    "what",
                    "why",
                    "the",
                    "and",
                    "for",
                    "with",
                    "work",
                    "is",
                    "are",
                    "our",
                    "you",
                }
                tokens = [t for t in tokens if t not in stop]
                seen_ids = set()
                all_objs: list[KnowledgeObject] = []
                for tok in tokens[:8]:
                    cand = self.store.metadata.query(filters={"query": tok}, limit=fetch_limit)
                    for c in cand:
                        if c.id not in seen_ids:
                            seen_ids.add(c.id)
                            all_objs.append(c)
                if all_objs:
                    objs = all_objs
            # score by occurrence + exact title boost
            scored: list[tuple[KnowledgeObject, float]] = []
            for o in objs:
                cnt = o.title.lower().count(query.lower()) + o.content.lower().count(query.lower())
                tokens = re.findall(r"\w+", query.lower())
                tokens = [t for t in tokens if len(t) > 2]
                tok_overlap = sum(
                    1 for t in tokens if t in o.title.lower() or t in o.content.lower()
                )
                # exact title match boost
                is_exact = o.title.lower() == query.lower().strip("?")
                exact_boost = 5.0 if is_exact else 0
                # entity type boost - reduced to avoid dominating relevance
                is_code = o.entity_type and o.entity_type.value in (
                    "CLASS",
                    "FUNCTION",
                    "METHOD",
                )
                type_boost = 0.2 if is_code else 0
                score = float(cnt + tok_overlap + 1) / 10.0 + exact_boost + type_boost
                scored.append((o, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            objs_sorted = [o for o, _ in scored[:top_k]]
            scores_sorted = [s for _, s in scored[:top_k]]
            return RetrievalResult(
                strategy="keyword",
                query=query,
                results=objs_sorted,
                scores=scores_sorted,
            )
        except Exception as e:
            logger.warning(f"keyword search failed: {e}")
            return RetrievalResult(strategy="keyword", query=query, results=[], scores=[])

    async def _graph_search(self, query: str, top_k: int = 10) -> RetrievalResult:
        try:
            # find nodes matching query then traverse
            candidates = self.store.metadata.query(filters={"query": query}, limit=5)
            if not candidates:
                return RetrievalResult(strategy="graph", query=query, results=[], scores=[])
            neighbors_ids: set[str] = set()
            for c in candidates:
                neigh = self.store.graph.get_neighbors(c.id, max_depth=2)
                neighbors_ids.update(neigh)
            # fetch KOs - batch query to avoid N+1
            truncated_ids = list(neighbors_ids)[:top_k]
            objs: list[KnowledgeObject] = []
            if truncated_ids:
                # prefer batch API if available, fallback to single gets
                if hasattr(self.store.metadata, "get_many"):
                    batch = self.store.metadata.get_many(truncated_ids)  # type: ignore[attr-defined]
                    objs = [ko for ko in batch if ko is not None]
                elif hasattr(self.store.metadata, "query") and truncated_ids:
                    # Use query with id filter if supported, else fallback
                    try:
                        cand = self.store.metadata.query(
                            filters={"ids": truncated_ids}, limit=top_k
                        )
                        # filter to ensure only requested ids
                        id_set = set(truncated_ids)
                        objs = [ko for ko in cand if ko.id in id_set]
                        if len(objs) < len(truncated_ids):
                            # fallback for any missing via get
                            missing = id_set - {ko.id for ko in objs}
                            for nid in missing:
                                ko = self.store.metadata.get(nid)
                                if ko:
                                    objs.append(ko)
                    except Exception:
                        # ultimate fallback: sequential gets
                        for nid in truncated_ids:
                            ko = self.store.metadata.get(nid)
                            if ko:
                                objs.append(ko)
                else:
                    for nid in truncated_ids:
                        ko = self.store.metadata.get(nid)
                        if ko:
                            objs.append(ko)
            scores = [0.7] * len(objs)
            return RetrievalResult(strategy="graph", query=query, results=objs, scores=scores)
        except Exception as e:
            logger.warning(f"graph search failed: {e}")
            return RetrievalResult(strategy="graph", query=query, results=[], scores=[])

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        strategies: list[str] | None = None,
        timeout: float = 0.2,
    ) -> tuple[list[tuple[KnowledgeObject, float]], dict]:
        strategies = strategies or ["vector", "keyword", "graph"]
        tasks = []
        if "vector" in strategies:
            tasks.append(self._vector_search(query, top_k))
        if "keyword" in strategies:
            tasks.append(self._keyword_search(query, top_k))
        if "graph" in strategies:
            tasks.append(self._graph_search(query, top_k))

        # run with timeout per strategy - concurrent via asyncio.gather
        results: list[RetrievalResult] = []
        if tasks:
            wrapped = [asyncio.wait_for(coro, timeout=timeout) for coro in tasks]
            gathered = await asyncio.gather(*wrapped, return_exceptions=True)
            for res in gathered:
                if isinstance(res, BaseException):
                    if isinstance(res, asyncio.TimeoutError):
                        logger.warning(f"Strategy timeout for query: {query}")
                    else:
                        logger.warning(f"Retrieval error: {res}")
                else:
                    results.append(res)  # type: ignore[arg-type]

        if not results:
            return [], {"vector": 0, "keyword": 0, "graph": 0}

        # fuse if multiple
        if len(results) > 1:
            fused = rrf_fuse(results, k=self.k)
        else:
            fused = [
                (obj, score)
                for obj, score in zip(results[0].results, results[0].scores, strict=True)
            ]

        stats = {r.strategy: len(r.results) for r in results}
        return fused[:top_k], stats

    async def retrieve_with_intent(
        self, query: str, intent: IntentType, weights: dict | None = None, top_k: int = 10
    ) -> tuple[list[tuple[KnowledgeObject, float]], dict]:
        # weights per intent could adjust strategies, for MVP just use all
        return await self.retrieve(query, top_k=top_k)
