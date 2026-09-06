"""Unified KnowledgeStore over metadata, vector, graph."""

from __future__ import annotations

import asyncio
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
        # Metadata is truth - atomic with outbox (offload blocking DB)
        await asyncio.to_thread(self.metadata.insert_many, knowledge)
        # fan-out to derived stores with per-KO success tracking
        succeeded_ids: set[str] = set()
        failed_ids: dict[str, str] = {}
        for ko in knowledge:
            vec_ok = True
            graph_ok = True
            try:
                await self.vector.upsert(ko, idempotency_key=ko.id)
            except Exception as e:
                vec_ok = False
                failed_ids[ko.id] = f"vector: {e}"
                logger.warning(f"Vector upsert failed for {ko.id}: {e}")
            try:
                await self.graph.upsert(ko, idempotency_key=ko.id)
            except Exception as e:
                graph_ok = False
                msg = f"graph: {e}"
                prev = failed_ids.get(ko.id, "")
                failed_ids[ko.id] = f"{prev}; {msg}" if prev else msg
                logger.warning(f"Graph upsert failed for {ko.id}: {e}")
            if vec_ok and graph_ok:
                succeeded_ids.add(ko.id)
        # mark outbox done — single claim per save batch, mark by id
        # ORDER BY created_at ensures FIFO; single claim avoids re-claiming same PENDING
        knowledge_ids = {ko.id for ko in knowledge}
        # batch = max(len(knowledge), 100) ensures we capture newly inserted rows
        # even when older PENDING exist; filtering by knowledge_ids scopes to this batch
        rows = await asyncio.to_thread(self.metadata.claim_outbox, max(len(knowledge), 100))
        for row in rows:
            if row.knowledge_id in knowledge_ids:
                if row.knowledge_id in succeeded_ids:
                    await asyncio.to_thread(self.metadata.mark_outbox_done, row.id)
                else:
                    err = failed_ids.get(row.knowledge_id, "fan-out failed")
                    await asyncio.to_thread(self.metadata.mark_outbox_failed, row.id, err)

    async def save_many(self, kos: list[KnowledgeObject]) -> None:
        await self.save(kos)

    async def reconcile_pending(self, batch: int = 100) -> int:
        """Reconcile pending/failed outbox entries: fan-out to derived stores.

        Called inline after save or via background cron (every 1m) and nightly
        check. Retries PENDING and FAILED entries (max 5 times via error field,
        alert thereafter — see storage-engine.md Reconciliation).
        Returns number of entries successfully reconciled (marked DONE).
        """
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from pkh.storage.metadata import OutboxRow

        reconciled = 0

        # Gather PENDING first (FIFO ORDER BY created_at via claim_outbox)
        pending_rows = await asyncio.to_thread(self.metadata.claim_outbox, batch)

        # Also gather FAILED for retry (simple: all FAILED ordered by created_at)
        def _claim_failed() -> list[OutboxRow]:
            with Session(self.metadata.engine) as session:
                rows = (
                    session.execute(
                        select(OutboxRow)
                        .where(OutboxRow.status == "FAILED")
                        .order_by(OutboxRow.created_at)
                        .limit(batch)
                    )
                    .scalars()
                    .all()
                )
                return rows

        failed_rows = await asyncio.to_thread(_claim_failed)
        # Dedup by id if any overlap (should not)
        seen: set[str] = set()
        all_rows: list[OutboxRow] = []
        for r in (*pending_rows, *failed_rows):
            if r.id not in seen:
                seen.add(r.id)
                all_rows.append(r)
            if len(all_rows) >= batch:
                break

        for row in all_rows:
            # DELETE op: remove from derived stores
            if row.op == "DELETE":
                try:
                    await self.vector.delete([row.knowledge_id])
                    await self.graph.delete_node(row.knowledge_id)
                    await asyncio.to_thread(self.metadata.mark_outbox_done, row.id)
                    reconciled += 1
                except Exception as e:
                    await asyncio.to_thread(self.metadata.mark_outbox_failed, row.id, str(e))
                continue
            # UPSERT op: reload KO from metadata truth and upsert derived
            ko = await asyncio.to_thread(self.metadata.get, row.knowledge_id)
            if ko is None:
                # KO deleted from metadata but outbox remains → mark done (no-op)
                await asyncio.to_thread(self.metadata.mark_outbox_done, row.id)
                continue
            try:
                await self.vector.upsert(ko, idempotency_key=ko.id)
                await self.graph.upsert(ko, idempotency_key=ko.id)
                await asyncio.to_thread(self.metadata.mark_outbox_done, row.id)
                reconciled += 1
            except Exception as e:
                await asyncio.to_thread(self.metadata.mark_outbox_failed, row.id, str(e))
        return reconciled

    async def nightly_check(self) -> dict[str, Any]:
        """Nightly consistency check (storage-engine.md:218).

        Compares count(metadata ACTIVE) vs count(vector) vs count(graph nodes).
        If drift >1% → needs_rebuild=True (derived stores rebuildable from
        Metadata via reconcile_pending or full rebuild). This is the
        "Nightly Consistency Check" concept; prod would run as cron nightly,
        MVP can call manually or after save.
        """
        metadata_count = await asyncio.to_thread(self.metadata.count)
        vector_count = await self.vector.count()
        graph_nodes = await self.graph.count_nodes()
        # drift ratios
        denom = max(1, metadata_count)
        drift_vector = abs(metadata_count - vector_count) / denom
        drift_graph = abs(metadata_count - graph_nodes) / denom
        needs_rebuild = drift_vector > 0.01 or drift_graph > 0.01
        return {
            "metadata_count": metadata_count,
            "vector_count": vector_count,
            "graph_nodes": graph_nodes,
            "graph_edges": await self.graph.count_edges(),
            "drift_vector": drift_vector,
            "drift_graph": drift_graph,
            "needs_rebuild": needs_rebuild,
            "note": (
                "Derived stores rebuildable from Metadata via "
                "reconcile_pending(); alert if needs_rebuild"
            ),
        }

    async def get(self, id: str) -> KnowledgeObject | None:
        return await asyncio.to_thread(self.metadata.get, id)

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
        # metadata keyword search (offload blocking DB)
        return await asyncio.to_thread(
            lambda: self.metadata.query(filters={"query": query, **filters}, limit=top_k)
        )

    async def get_by_source(self, source_id: str) -> list[KnowledgeObject]:
        return await asyncio.to_thread(self.metadata.get_by_source, source_id)

    async def get_relationships(self, entity_id: str) -> list[str]:
        return await asyncio.to_thread(self.graph.get_neighbors, entity_id)

    async def delete(self, id: str) -> None:
        await asyncio.to_thread(self.metadata.delete, id)
        await self.vector.delete([id])
        await self.graph.delete_node(id)

    async def count(self) -> int:
        return await asyncio.to_thread(self.metadata.count)

    async def health_check(self) -> dict[str, Any]:
        return {
            "metadata_count": await asyncio.to_thread(self.metadata.count),
            "vector_count": await self.vector.count(),
            "graph_nodes": await self.graph.count_nodes(),
            "graph_edges": await self.graph.count_edges(),
        }
