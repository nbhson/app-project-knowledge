"""Document connector - local filesystem."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentConnector:
    source_type = SourceType.DOCUMENT

    def __init__(self, paths: list[str] | None = None, patterns: list[str] | None = None):
        self.paths = [Path(p) for p in (paths or ["./docs"])]
        self.patterns = patterns or ["*.md", "*.pdf", "*.yaml", "*.json"]

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        items: list[RawItem] = []
        import fnmatch

        for base in self.paths:
            if not base.exists():
                continue
            for file in base.rglob("*"):
                if not file.is_file():
                    continue
                matched = any(fnmatch.fnmatch(file.name, pat) for pat in self.patterns) or any(
                    fnmatch.fnmatch(str(file), pat) for pat in self.patterns
                )
                # if pattern like *.md, check suffix
                if not matched:
                    # allow all if patterns empty
                    continue
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                rel = str(file)
                items.append(
                    RawItem(
                        item_id=rel,
                        source_type=SourceType.DOCUMENT.value,
                        title=file.name,
                        content=content,
                        content_type=file.suffix.lstrip(".") or "text",
                        metadata={"file_path": rel, "format": file.suffix},
                        updated_at=datetime.now(timezone.utc),
                    )
                )
        return items

    async def get_item(self, item_id: str) -> RawItem:
        items = await self.list_items()
        for it in items:
            if it.item_id == item_id:
                return it
        raise FileNotFoundError(item_id)

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        # simple: return all with mtime > since
        items = await self.list_items()
        result = []
        for it in items:
            p = Path(it.item_id)
            if p.exists() and datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) > since:
                result.append(it)
        return result

    def health_check(self) -> bool:
        return any(p.exists() for p in self.paths)
