"""Shared runtime helpers: process-level store cache (CLI + API).

Round 2 dedup: `cli/main.py` and `api/main.py` previously carried identical
copies of the singleton store logic (`_store_key_from_settings`, `_create_store`,
lazy get). This module owns it once, thread-safe.
"""

from __future__ import annotations

import threading

from pkh.config.settings import Settings, get_settings
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import get_logger

logger = get_logger(__name__)

StoreKey = tuple[str, str, str]


def store_key_from_settings(settings: Settings | None = None) -> StoreKey:
    s = settings or get_settings()
    return (
        s.storage.metadata.sqlite_path,
        s.storage.vector.path,
        s.storage.graph.persist_path,
    )


def create_store(settings: Settings | None = None) -> KnowledgeStore:
    s = settings or get_settings()
    return KnowledgeStore(
        metadata_path=s.storage.metadata.sqlite_path,
        vector_path=s.storage.vector.path,
        graph_path=s.storage.graph.persist_path,
    )


class SharedStore:
    """Process-level KnowledgeStore cache keyed by configured storage paths."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: KnowledgeStore | None = None
        self._key: StoreKey | None = None

    def get(self) -> KnowledgeStore:
        key = store_key_from_settings()
        with self._lock:
            if self._store is None or self._key != key:
                self._store = create_store()
                self._key = key
            return self._store

    def close(self) -> None:
        """Dispose resources and clear the cache (used on API shutdown)."""
        with self._lock:
            if self._store is not None:
                try:
                    self._store.close()
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning(f"store close: {e}")
                self._store = None
                self._key = None
