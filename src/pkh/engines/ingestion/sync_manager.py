"""SyncManager orchestrates all connectors."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

from pkh.engines.ingestion.models import RawItem, SyncResult
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class SyncManager:
    def __init__(self, connectors: list | None = None):
        self.connectors = connectors or []
        self._cursors: dict[str, str] = {}

    def register(self, connector) -> None:
        self.connectors.append(connector)

    async def _sync_one(self, conn) -> tuple[list[RawItem], str | None]:
        try:
            await conn.connect()
        except Exception as e:
            return [], f"{conn.source_type}: {e}"
        try:
            items = await conn.list_items(cursor=self._cursors.get(str(conn.source_type)))
            if items:
                self._cursors[str(conn.source_type)] = items[-1].item_id
            return items, None
        except Exception as e:
            return [], f"{conn.source_type}: {e}"
        finally:
            try:
                await conn.disconnect()
            except Exception:
                pass

    async def run_full_sync(self) -> SyncResult:
        start = time.time()
        total = 0
        errors: list[str] = []
        all_items: list[RawItem] = []
        # concurrent across connectors
        results = await asyncio.gather(*[self._sync_one(c) for c in self.connectors])
        for items, err in results:
            if err:
                errors.append(err)
                logger.warning(f"Sync failed: {err}")
            all_items.extend(items)
            total += len(items)
        # collect errors separately to keep items even on partial failure
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
        all_items: list[RawItem] = []

        async def _incr(conn):
            await conn.connect()
            try:
                return await conn.detect_changes(since)
            finally:
                try:
                    await conn.disconnect()
                except Exception:
                    pass

        results = await asyncio.gather(*[_incr(c) for c in self.connectors], return_exceptions=True)
        for conn, res in zip(self.connectors, results, strict=False):
            if isinstance(res, BaseException):
                errors.append(f"{conn.source_type}: {res}")
                logger.warning(f"Sync failed for {conn.source_type}: {res}")
            else:
                total += len(res)
                all_items.extend(res)
        return SyncResult(
            total_items_processed=total,
            new_items=total,
            errors=errors,
            duration_seconds=time.time() - start,
        )

    async def sync_source(self, source_type: str) -> list[RawItem]:
        st = source_type.strip().lower()
        for conn in self.connectors:
            ctype = getattr(conn.source_type, "value", str(conn.source_type)).lower()
            if ctype == st or str(conn.source_type).lower() == st:
                await conn.connect()
                try:
                    return await conn.list_items()
                finally:
                    try:
                        await conn.disconnect()
                    except Exception:
                        pass
        return []

    async def collect_all(self) -> list[RawItem]:
        # concurrent + cursor tracking + disconnect (dedup with run_full_sync)
        results = await asyncio.gather(*[self._sync_one(c) for c in self.connectors])
        items: list[RawItem] = []
        for batch, _ in results:
            items.extend(batch)
        return items
