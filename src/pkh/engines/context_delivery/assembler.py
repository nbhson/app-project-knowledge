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
                content=ko.content[:4000],
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

        # deduplicate sources by (source_type, source_id)
        seen = set()
        uniq_sources = []
        for sr in all_sources:
            key = (sr.source_type.value, sr.source_id)
            if key not in seen:
                seen.add(key)
                uniq_sources.append(sr)

        # relationships: fetch graph edges for top chunks
        relationships: list[RelationshipChunk] = []
        for ko, _ in ranked[:5]:
            neigh_ids = self.store.graph.get_neighbors(ko.id, max_depth=1)
            for nid in neigh_ids[:3]:
                # find edge data
                if self.store.graph.graph.has_edge(ko.id, nid):
                    edge = self.store.graph.graph.get_edge_data(ko.id, nid) or {}
                    rel_type = edge.get("relation", "RELATED_TO")
                    conf = edge.get("confidence", 0.8)
                    relationships.append(
                        RelationshipChunk(from_id=ko.id, to_id=nid, type=rel_type, confidence=conf)  # type: ignore
                    )
                elif self.store.graph.graph.has_edge(nid, ko.id):
                    edge = self.store.graph.graph.get_edge_data(nid, ko.id) or {}
                    rel_type = edge.get("relation", "RELATED_TO")
                    conf = edge.get("confidence", 0.8)
                    relationships.append(
                        RelationshipChunk(from_id=nid, to_id=ko.id, type=rel_type, confidence=conf)  # type: ignore
                    )

        overall_conf = float(statistics.mean(confidences)) if confidences else 0.0

        # warnings
        low_conf = sum(1 for c in confidences if c < 0.5)
        if low_conf:
            warnings.append(f"{low_conf} low-confidence chunks included")

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
            compression_ratio=1.0,
        )
