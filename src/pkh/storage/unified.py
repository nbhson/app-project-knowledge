"""Unified KnowledgeStore over metadata, vector, graph."""

from __future__ import annotations

from typing import Any

from pkh.models.knowledge import KnowledgeObject
from pkh.storage.graph import GraphStore
from pkh.storage.metadata import MetadataStore
from pkh.storage.vector import ChromaVectorStore
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class KnowledgeStore:
    def __init__(
        self,
        metadata_path: str = "./data/pkh.db",
        vector_path: str = "./data/chroma",
        graph_path: str = "./data/graph.json",
    ):
        self.metadata = MetadataStore(sqlite_path=metadata_path)
        self.vector = ChromaVectorStore(path=vector_path)
        self.graph = GraphStore(persist_path=graph_path)

    async def save(self, knowledge: KnowledgeObject | list[KnowledgeObject]) -> None:
        if isinstance(knowledge, KnowledgeObject):
            knowledge = [knowledge]
        # Metadata is truth - atomic with outbox
        self.metadata.insert_many(knowledge)
        # fan-out to derived stores
        for ko in knowledge:
            try:
                await self.vector.upsert(ko, idempotency_key=ko.id)
            except Exception as e:
                logger.warning(f"Vector upsert failed for {ko.id}: {e}")
            try:
                await self.graph.upsert(ko, idempotency_key=ko.id)
            except Exception as e:
                logger.warning(f"Graph upsert failed for {ko.id}: {e}")
        # mark outbox done (simple inline)
        for ko in knowledge:
            # find pending outbox for this ko and mark done
            rows = self.metadata.claim_outbox(batch=100)
            for row in rows:
                if row.knowledge_id == ko.id:
                    self.metadata.mark_outbox_done(row.id)

    async def save_many(self, kos: list[KnowledgeObject]) -> None:
        await self.save(kos)

    async def get(self, id: str) -> KnowledgeObject | None:
        return self.metadata.get(id)

    async def search(
        self, query: str, filters: dict[str, Any] | None = None, top_k: int = 10
    ) -> list[KnowledgeObject]:
        filters = filters or {}
        # Try vector first, fallback to metadata
        try:
            vector_results = await self.vector.query(query, top_k=top_k, filters=filters)
            if vector_results:
                return [ko for ko, _score in vector_results]
        except Exception as e:
            logger.warning(f"Vector search failed, fallback to metadata: {e}")
        # metadata keyword search
        return self.metadata.query(filters={"query": query, **filters}, limit=top_k)

    async def get_by_source(self, source_id: str) -> list[KnowledgeObject]:
        return self.metadata.get_by_source(source_id)

    async def get_relationships(self, entity_id: str) -> list[str]:
        return self.graph.get_neighbors(entity_id)

    async def delete(self, id: str) -> None:
        self.metadata.delete(id)
        await self.vector.delete([id])
        await self.graph.delete_node(id)

    async def count(self) -> int:
        return self.metadata.count()

    async def health_check(self) -> dict[str, Any]:
        return {
            "metadata_count": self.metadata.count(),
            "vector_count": await self.vector.count(),
            "graph_nodes": await self.graph.count_nodes(),
            "graph_edges": await self.graph.count_edges(),
        }
