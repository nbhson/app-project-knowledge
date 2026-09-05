"""Base connector interface."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType


class SourceConnector(Protocol):
    source_type: SourceType

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def list_items(self, cursor: str | None = None) -> list[RawItem]: ...
    async def get_item(self, item_id: str) -> RawItem: ...
    async def detect_changes(self, since: datetime) -> list[RawItem]: ...
    def health_check(self) -> bool: ...
