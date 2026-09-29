"""Document connector - local filesystem with optimized pattern matching."""

from __future__ import annotations

import fnmatch
import re
from datetime import datetime, timezone
from pathlib import Path

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)

# Default patterns synced with config/settings.yaml.example
DEFAULT_PATTERNS: list[str] = ["*.md", "*.pdf", "*.yaml", "*.json", "*.yml", "*.txt", "*.rst"]


class DocumentConnector:
    source_type = SourceType.DOCUMENT

    def __init__(self, paths: list[str] | None = None, patterns: list[str] | None = None):
        self.paths = [Path(p) for p in (paths or ["./docs"])]
        self.patterns = patterns or DEFAULT_PATTERNS.copy()
        # Precompute optimized matching structures to avoid O(P*N) fnmatch per file
        # For simple "*.ext" patterns we use suffix set O(1); remaining globs compiled to regex
        self._suffixes: set[str] = set()
        self._compiled: list[re.Pattern[str]] = []
        self._name_compiled: list[re.Pattern[str]] = []
        self._path_compiled: list[re.Pattern[str]] = []
        self._build_matchers()

    def _build_matchers(self) -> None:
        suffixes: set[str] = set()
        name_pats: list[str] = []
        path_pats: list[str] = []
        for pat in self.patterns:
            # simple "*.ext" without slash and single wildcard -> suffix set
            is_simple = pat.startswith("*.") and "/" not in pat
            is_simple = is_simple and pat.count("*") == 1 and pat.count("?") == 0
            if is_simple:
                # e.g. "*.md" -> ".md"
                suffix = pat[1:]  # ".md"
                # ensure no other glob chars
                if suffix and all(c not in suffix for c in "*?["):
                    suffixes.add(suffix.lower())
                    continue
            # classify as name vs path pattern
            if "/" in pat or "**" in pat:
                path_pats.append(pat)
            else:
                name_pats.append(pat)
        self._suffixes = suffixes
        self._name_compiled = [re.compile(fnmatch.translate(p)) for p in name_pats]
        self._path_compiled = [re.compile(fnmatch.translate(p)) for p in path_pats]
        # keep combined for fallback
        self._compiled = self._name_compiled + self._path_compiled

    def _matches(self, file: Path) -> bool:
        if not self.patterns:
            return True
        # fast suffix check O(1)
        if file.suffix.lower() in self._suffixes:
            return True
        name = file.name
        f_str = str(file)
        for rx in self._name_compiled:
            if rx.match(name):
                return True
        for rx in self._path_compiled:
            if rx.match(f_str) or rx.match(name):
                return True
        return False

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        import asyncio

        items: list[RawItem] = []

        async def _read_file(file: Path) -> RawItem | None:
            try:
                content = await asyncio.to_thread(file.read_text, encoding="utf-8", errors="ignore")
            except Exception:
                return None
            if not content.strip():
                return None
            rel = str(file)
            try:
                mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
            except Exception:
                mtime = datetime.now(timezone.utc)
            return RawItem(
                item_id=rel,
                source_type=SourceType.DOCUMENT.value,
                title=file.name,
                content=content,
                content_type=file.suffix.lstrip(".") or "text",
                metadata={"file_path": rel, "format": file.suffix},
                updated_at=mtime,
            )

        for base in self.paths:
            if not base.exists():
                continue
            files = [f for f in base.rglob("*") if f.is_file() and self._matches(f)]
            # concurrent reads to avoid blocking loop
            results = await asyncio.gather(*[_read_file(f) for f in files[:2000]])
            items.extend([r for r in results if r is not None])
        # cache for O(1) get_item
        self._cache = {it.item_id: it for it in items}
        return items

    async def get_item(self, item_id: str) -> RawItem:
        cache = getattr(self, "_cache", {})
        if item_id in cache:
            return cache[item_id]
        p = Path(item_id)
        if p.is_file() and self._matches(p):
            try:
                import asyncio

                content = await asyncio.to_thread(p.read_text, encoding="utf-8", errors="ignore")
                return RawItem(
                    item_id=item_id,
                    source_type=SourceType.DOCUMENT.value,
                    title=p.name,
                    content=content,
                    content_type=p.suffix.lstrip(".") or "text",
                    metadata={"file_path": item_id, "format": p.suffix},
                    updated_at=datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc),
                )
            except Exception as e:
                raise FileNotFoundError(f"{item_id}: {e}") from e
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
