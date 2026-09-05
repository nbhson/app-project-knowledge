"""SyncManager orchestrates all connectors."""

from __future__ import annotations

import time
from datetime import datetime

from pkh.engines.ingestion.models import RawItem, SyncResult
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class SyncManager:
    def __init__(self, connectors: list | None = None):
        self.connectors = connectors or []

    def register(self, connector) -> None:
        self.connectors.append(connector)

    async def run_full_sync(self) -> SyncResult:
        start = time.time()
        total = 0
        errors: list[str] = []
        all_items: list[RawItem] = []
        for conn in self.connectors:
            try:
                await conn.connect()
                items = await conn.list_items()
                all_items.extend(items)
                total += len(items)
                logger.info(f"Synced {len(items)} items from {conn.source_type}")
            except Exception as e:
                errors.append(f"{conn.source_type}: {e}")
                logger.warning(f"Sync failed for {conn.source_type}: {e}")
        return SyncResult(
            total_items_processed=total,
            new_items=total,
            errors=errors,
            duration_seconds=time.time() - start,
        )

    async def run_incremental_sync(self, since: datetime) -> SyncResult:
        start = time.time()
        total = 0
        errors: list[str] = []
        for conn in self.connectors:
            try:
                await conn.connect()
                items = await conn.detect_changes(since)
                total += len(items)
            except Exception as e:
                errors.append(f"{conn.source_type}: {e}")
        return SyncResult(
            total_items_processed=total,
            new_items=total,
            errors=errors,
            duration_seconds=time.time() - start,
        )

    async def sync_source(self, source_type: str) -> list[RawItem]:
        for conn in self.connectors:
            if (
                str(conn.source_type.value).lower() == source_type.lower()
                or str(conn.source_type).lower() == source_type.lower()
            ):
                await conn.connect()
                return await conn.list_items()
        return []

    async def collect_all(self) -> list[RawItem]:
        items: list[RawItem] = []
        for conn in self.connectors:
            await conn.connect()
            items.extend(await conn.list_items())
        return items
