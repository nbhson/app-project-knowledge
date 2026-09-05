"""RawItem and sync result models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    item_id: str
    source_type: str
    title: str
    content: str
    content_type: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class SyncResult(BaseModel):
    total_items_processed: int = 0
    new_items: int = 0
    updated_items: int = 0
    deleted_items: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class SourceSyncResult(BaseModel):
    source_type: str
    source_id: str
    items: list[RawItem] = Field(default_factory=list)
    error: str | None = None
