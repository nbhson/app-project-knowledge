"""Vector store - ChromaDB with in-memory fallback."""

from __future__ import annotations

import hashlib
from typing import Any

from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    LifecycleState,
    ObjectType,
    SourceReference,
    SourceType,
)
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


def _simple_embedding(text: str, dim: int = 64) -> list[float]:
    # deterministic hash-based embedding for MVP without openai
    # TODO: respect settings.vector.embedding_model when OPENAI_API_KEY set
    #   -> replace hash with text-embedding-3-small via openai embeddings API
    #   Keep hash fallback when embedding_model == "hash" or no API key.
    h = hashlib.sha256(text.encode()).digest()
    # expand
    vals = []
    for i in range(dim):
        vals.append((h[i % len(h)] / 255.0) * 2 - 1)
    # normalize
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


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
            self._reconcile()
        except Exception as e:
            logger.warning(f"Chroma not available, using in-memory fallback: {e}")
            self._use_fallback = True

    def _reconcile(self) -> None:
        """Warm fallback cache from Chroma on startup (restart persistence).

        Sync existing Chroma entries into fallback store so queries survive
        via fallback lookup when Chroma is temporarily unavailable, and so
        query can map Chroma ids back to KnowledgeObjects.
        Best-effort: reconstruction from metadata+document if fallback miss.
        """
        if self._use_fallback or self._collection is None:
            return
        try:
            # include embeddings to avoid recompute drift
            data = self._collection.get(include=["embeddings", "metadatas", "documents"])
            ids: list[str] = data.get("ids") or []
            if not ids:
                return
            metadatas: list[dict[str, Any]] = data.get("metadatas") or []
            documents: list[str | None] = data.get("documents") or []
            embeddings: list[list[float] | None] = data.get("embeddings") or []
            for idx, ko_id in enumerate(ids):
                if ko_id in self._fallback.store:
                    continue
                md = metadatas[idx] if idx < len(metadatas) and metadatas[idx] is not None else {}
                doc = documents[idx] if idx < len(documents) and documents[idx] is not None else ""
                emb = embeddings[idx] if idx < len(embeddings) else None
                # Reconstruct minimal KO from stored metadata/document
                try:
                    entity_type_val = md.get("entity_type") or ""
                    entity_type = EntityType(entity_type_val) if entity_type_val else None
                except Exception:
                    entity_type = None
                try:
                    ls_val = md.get("lifecycle_state") or LifecycleState.ACTIVE.value
                    LifecycleState(ls_val)
                except Exception:
                    ls_val = LifecycleState.ACTIVE.value
                confidence = (
                    float(md.get("confidence", 0.5))
                    if isinstance(md.get("confidence"), (int, float, str))
                    else 0.5
                )
                title = md.get("title") or ko_id
                content = doc or title
                # need at least one source_reference; use placeholder that
                # reconciles later via metadata store
                sr = SourceReference(source_type=SourceType.GIT, source_id="reconciled", url=None)
                try:
                    ko_kwargs: dict[str, Any] = {
                        "id": ko_id,
                        "title": title,
                        "content": content,
                        "source_references": [sr],
                        "confidence": max(0.0, min(1.0, confidence)),
                        "lifecycle_state": LifecycleState(ls_val),
                    }
                    # object_type required; default ENTITY if entity_type present else ENTITY
                    ko_kwargs["object_type"] = ObjectType.ENTITY
                    if entity_type is not None:
                        ko_kwargs["entity_type"] = entity_type
                    else:
                        # choose FILE as generic ENTITY type when unknown
                        ko_kwargs["entity_type"] = EntityType.FILE
                    ko = KnowledgeObject(**ko_kwargs)
                except Exception:
                    continue
                text = f"{ko.title} {ko.description or ''} {ko.content}"
                if emb is None:
                    emb = _simple_embedding(text)
                # Store in fallback format compatible with InMemoryVectorStore.query
                self._fallback.store[ko_id] = {
                    "id": ko_id,
                    "embedding": list(emb) if emb is not None else _simple_embedding(text),
                    "content": text,
                    "metadata": {
                        "entity_type": entity_type.value if entity_type else "",
                        "lifecycle_state": ls_val,
                        "confidence": confidence,
                        "title": title,
                    },
                    "ko": ko,
                }
            if ids:
                logger.info(f"Vector reconcile: warmed {len(ids)} ids into fallback cache")
        except Exception as e:
            logger.warning(f"Vector reconcile failed: {e}")

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
            return
        # Dual-write symmetric: keep fallback warm on success (fallback only on exception above)
        try:
            await self._fallback.upsert(ko, idempotency_key)
        except Exception as e:
            logger.warning(f"Fallback upsert after Chroma success failed: {e}")

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
            # Respect filters as Chroma where clause if simple; otherwise
            # post-filter. For MVP post-filter on lifecycle_states to keep
            # behavior consistent with fallback.
            res = self._collection.query(query_embeddings=[q_emb], n_results=top_k)
            # res shape: {"ids": [[...]], "distances": [[...]],
            # "metadatas": [[...]], "documents": [[...]]}
            ids: list[str] = res.get("ids", [[]])[0] if res.get("ids") else []
            distances: list[float] = res.get("distances", [[]])[0] if res.get("distances") else []
            metadatas: list[dict[str, Any]] = (
                res.get("metadatas", [[]])[0] if res.get("metadatas") else []
            )
            documents: list[str | None] = (
                res.get("documents", [[]])[0]
                if res.get("documents")
                else []
                if "documents" in res
                else []
            )

            if not ids:
                return []

            scored: list[tuple[KnowledgeObject, float]] = []
            for idx, ko_id in enumerate(ids):
                dist = (
                    float(distances[idx])
                    if idx < len(distances) and distances[idx] is not None
                    else 0.0
                )
                score = 1.0 / (1.0 + dist)
                md: dict[str, Any] = (
                    metadatas[idx] if idx < len(metadatas) and metadatas[idx] is not None else {}
                )
                # respect filters if present
                if filters and "lifecycle_states" in filters:
                    if md.get("lifecycle_state") not in filters["lifecycle_states"]:
                        continue
                # Map Chroma id back to KnowledgeObject via fallback cache
                entry = self._fallback.store.get(ko_id)
                if entry is not None:
                    ko = entry["ko"]
                else:
                    # Fallback miss (e.g., after restart before reconcile or external write)
                    # Reconstruct minimal KO from Chroma metadata+document
                    doc = (
                        documents[idx]
                        if idx < len(documents) and documents[idx] is not None
                        else ""
                    )
                    try:
                        entity_type_val = md.get("entity_type") or ""
                        entity_type = EntityType(entity_type_val) if entity_type_val else None
                    except Exception:
                        entity_type = None
                    ls_val = md.get("lifecycle_state") or LifecycleState.ACTIVE.value
                    try:
                        LifecycleState(ls_val)
                    except Exception:
                        ls_val = LifecycleState.ACTIVE.value
                    confidence = (
                        float(md.get("confidence", 0.5))
                        if isinstance(md.get("confidence"), (int, float, str))
                        else 0.5
                    )
                    title = md.get("title") or ko_id
                    content = doc or title
                    sr = SourceReference(
                        source_type=SourceType.GIT, source_id="reconciled", url=None
                    )
                    try:
                        ko_kwargs2: dict[str, Any] = {
                            "id": ko_id,
                            "title": title,
                            "content": content,
                            "source_references": [sr],
                            "confidence": max(0.0, min(1.0, confidence)),
                            "lifecycle_state": LifecycleState(ls_val),
                            "object_type": ObjectType.ENTITY,
                        }
                        if entity_type is not None:
                            ko_kwargs2["entity_type"] = entity_type
                        else:
                            ko_kwargs2["entity_type"] = EntityType.FILE
                        ko = KnowledgeObject(**ko_kwargs2)
                    except Exception:
                        continue
                    # Warm fallback for next time
                    text = f"{ko.title} {ko.description or ''} {ko.content}"
                    self._fallback.store[ko_id] = {
                        "id": ko_id,
                        "embedding": _simple_embedding(text),
                        "content": text,
                        "metadata": {
                            "entity_type": entity_type.value if entity_type else "",
                            "lifecycle_state": ls_val,
                            "confidence": confidence,
                            "title": title,
                        },
                        "ko": ko,
                    }
                scored.append((ko, score))

            # Distances already sorted ascending => scores descending, but re-sort for filter cases
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]
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
