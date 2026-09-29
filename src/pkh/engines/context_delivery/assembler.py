"""Context assembler."""

from __future__ import annotations

import statistics

from pkh.engines.context_delivery.models import (
    ContextPackage,
    KnowledgeChunk,
    RelationshipChunk,
    SearchStats,
)
from pkh.engines.retrieval.intent import IntentType
from pkh.models.knowledge import KnowledgeObject
from pkh.storage.unified import KnowledgeStore


def _truncate_to_tokens(text: str, max_tokens: int = 4000) -> str:
    """Truncate text to max_tokens via tiktoken if available, fallback to chars."""
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) > max_tokens:
            return enc.decode(tokens[:max_tokens])
        return text
    except Exception:
        # fallback: approx 4 chars per token
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            return text[:max_chars]
        return text


class ContextAssembler:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def assemble(
        self,
        query: str,
        ranked: list[tuple[KnowledgeObject, float]],
        intent: IntentType | str = "",
        search_stats: SearchStats | None = None,
        warnings: list[str] | None = None,
    ) -> ContextPackage:
        warnings = warnings or []
        chunks: list[KnowledgeChunk] = []
        all_sources = []
        states: set[str] = set()
        confidences: list[float] = []

        for rank, (ko, score) in enumerate(ranked, start=1):
            et = ko.entity_type.value if ko.entity_type else ko.object_type.value
            chunk = KnowledgeChunk(
                id=ko.id,
                type=et,  # type: ignore
                title=ko.title,
                content=_truncate_to_tokens(ko.content, 4000),
                confidence=ko.confidence,
                lifecycle_state=ko.lifecycle_state.value,  # type: ignore
                relevance_score=float(score),
                rank=rank,
                sources=ko.source_references,
            )
            chunks.append(chunk)
            all_sources.extend(ko.source_references)
            states.add(ko.lifecycle_state.value)
            confidences.append(ko.confidence)

        # deduplicate sources by url if present, else (source_type, source_id)
        seen = set()
        uniq_sources = []
        for sr in all_sources:
            key = sr.url if sr.url else (sr.source_type.value, sr.source_id)
            if key not in seen:
                seen.add(key)
                uniq_sources.append(sr)

        # relationships: fetch graph edges for top chunks
        relationships: list[RelationshipChunk] = []
        for ko, _ in ranked[:5]:
            neigh_ids = self.store.graph.get_neighbors(ko.id, max_depth=1)
            for nid in neigh_ids[:3]:
                # use public accessors (do not touch .graph internals)
                edge = None
                from_id, to_id = ko.id, nid
                if hasattr(self.store.graph, "get_edge"):
                    edge = self.store.graph.get_edge(ko.id, nid)
                    if edge is None:
                        edge = self.store.graph.get_edge(nid, ko.id)
                        if edge is not None:
                            from_id, to_id = nid, ko.id
                else:  # fallback for custom stores
                    g = getattr(self.store.graph, "graph", None)
                    if g is not None:
                        if g.has_edge(ko.id, nid):
                            edge = dict(g.get_edge_data(ko.id, nid) or {})
                        elif g.has_edge(nid, ko.id):
                            edge = dict(g.get_edge_data(nid, ko.id) or {})
                            from_id, to_id = nid, ko.id
                if edge is None:
                    continue
                rel_type = edge.get("relation", "RELATED_TO")
                conf = float(edge.get("confidence", 0.8))
                relationships.append(
                    RelationshipChunk(from_id=from_id, to_id=to_id, type=rel_type, confidence=conf)  # type: ignore
                )

        overall_conf = float(statistics.mean(confidences)) if confidences else 0.0

        # warnings
        low_conf = sum(1 for c in confidences if c < 0.5)
        if low_conf:
            warnings.append(f"{low_conf} low-confidence chunks included")

        # actual compression ratio: raw vs truncated chars
        raw_chars = sum(len(ko.content) for ko, _ in ranked)
        kept_chars = sum(len(c.content) for c in chunks)
        ratio = (raw_chars / max(1, kept_chars)) if kept_chars else 1.0

        return ContextPackage(
            query=query,
            knowledge=chunks,
            relationships=relationships,
            confidence=overall_conf,
            sources=uniq_sources,
            lifecycle_states=sorted(states),
            warnings=warnings,
            intent=intent.value if isinstance(intent, IntentType) else str(intent),
            search_stats=search_stats,
            compression_ratio=round(ratio, 3),
        )
