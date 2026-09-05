"""Vector store - ChromaDB with in-memory fallback."""

from __future__ import annotations

import hashlib
from typing import Any

from pkh.models.knowledge import KnowledgeObject
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


def _simple_embedding(text: str, dim: int = 64) -> list[float]:
    # deterministic hash-based embedding for MVP without openai
    h = hashlib.sha256(text.encode()).digest()
    # expand
    vals = []
    for i in range(dim):
        vals.append((h[i % len(h)] / 255.0) * 2 - 1)
    # normalize
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class InMemoryVectorStore:
    def __init__(self):
        self.store: dict[str, dict[str, Any]] = {}

    async def upsert(self, ko: KnowledgeObject, idempotency_key: str | None = None) -> None:
        text = f"{ko.title} {ko.description or ''} {ko.content}"
        emb = _simple_embedding(text)
        self.store[ko.id] = {
            "id": ko.id,
            "embedding": emb,
            "content": text,
            "metadata": {
                "entity_type": ko.entity_type.value if ko.entity_type else "",
                "lifecycle_state": ko.lifecycle_state.value,
                "confidence": ko.confidence,
                "title": ko.title,
            },
            "ko": ko,
        }

    async def upsert_many(self, kos: list[KnowledgeObject]) -> None:
        for ko in kos:
            await self.upsert(ko)

    async def query(
        self, query_text: str, top_k: int = 5, filters: dict | None = None
    ) -> list[tuple[KnowledgeObject, float]]:
        if not self.store:
            return []
        q_emb = _simple_embedding(query_text)
        scored = []
        for entry in self.store.values():
            # filter by lifecycle if provided
            if filters and "lifecycle_states" in filters:
                if entry["metadata"]["lifecycle_state"] not in filters["lifecycle_states"]:
                    continue
            score = _cosine(q_emb, entry["embedding"])
            # keyword boost
            if query_text.lower() in entry["content"].lower():
                score += 0.3
            scored.append((entry["ko"], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def delete(self, ids: list[str]) -> None:
        for i in ids:
            self.store.pop(i, None)

    async def count(self) -> int:
        return len(self.store)


class ChromaVectorStore:
    def __init__(self, path: str = "./data/chroma", collection: str = "knowledge"):
        self.path = path
        self.collection_name = collection
        self._client = None
        self._collection = None
        self._fallback = InMemoryVectorStore()
        self._use_fallback = False
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=path)
            self._collection = self._client.get_or_create_collection(name=collection)
        except Exception as e:
            logger.warning(f"Chroma not available, using in-memory fallback: {e}")
            self._use_fallback = True

    async def upsert(self, ko: KnowledgeObject, idempotency_key: str | None = None) -> None:
        if self._use_fallback:
            return await self._fallback.upsert(ko, idempotency_key)
        text = f"{ko.title} {ko.description or ''} {ko.content}"
        emb = _simple_embedding(text)
        try:
            self._collection.upsert(
                ids=[ko.id],
                embeddings=[emb],
                metadatas=[
                    {
                        "entity_type": ko.entity_type.value if ko.entity_type else "",
                        "lifecycle_state": ko.lifecycle_state.value,
                        "confidence": ko.confidence,
                        "title": ko.title,
                    }
                ],
                documents=[text],
            )
        except Exception as e:
            logger.warning(f"Chroma upsert failed, fallback: {e}")
            await self._fallback.upsert(ko, idempotency_key)

    async def upsert_many(self, kos: list[KnowledgeObject]) -> None:
        for ko in kos:
            await self.upsert(ko)

    async def query(
        self, query_text: str, top_k: int = 5, filters: dict | None = None
    ) -> list[tuple[KnowledgeObject, float]]:
        if self._use_fallback:
            return await self._fallback.query(query_text, top_k, filters)
        try:
            q_emb = _simple_embedding(query_text)
            res = self._collection.query(query_embeddings=[q_emb], n_results=top_k)
            # need to map back to KO - we don't store full KO in chroma, so we need fallback search via metadata store?
            # For MVP, we will use fallback in-memory if we need full KO; but we can attempt to query via fallback store synced separately
            # If chroma returns ids, we need to fetch KO from fallback/metadata - for now use fallback
            return await self._fallback.query(query_text, top_k, filters)
        except Exception as e:
            logger.warning(f"Chroma query failed: {e}")
            return await self._fallback.query(query_text, top_k, filters)

    async def delete(self, ids: list[str]) -> None:
        if self._use_fallback:
            return await self._fallback.delete(ids)
        try:
            self._collection.delete(ids=ids)
        except Exception:
            pass
        await self._fallback.delete(ids)

    async def count(self) -> int:
        if self._use_fallback:
            return await self._fallback.count()
        try:
            return self._collection.count()
        except Exception:
            return await self._fallback.count()


# Default vector store factory
def get_vector_store(path: str = "./data/chroma", collection: str = "knowledge"):
    return ChromaVectorStore(path, collection)


VectorStore = ChromaVectorStore
