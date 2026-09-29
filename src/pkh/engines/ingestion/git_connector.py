"""Git connector - clone/pull, list files, change detection."""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.exceptions import SourceError
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


async def _run(cmd: list[str], cwd: Path | None = None) -> str:
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, cwd=cwd, timeout=30
    )
    if result.returncode != 0:
        raise SourceError(f"git command failed {' '.join(cmd)}: {result.stderr}")
    return result.stdout.strip()


EXT_LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".js": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


class GitConnector:
    source_type = SourceType.GIT

    def __init__(
        self,
        repo_url: str,
        branch: str = "main",
        local_path: str | Path | None = None,
        auth_type: str = "none",
        shallow: bool = False,
    ):
        self.repo_url = repo_url
        self.branch = branch
        self.auth_type = auth_type
        self.shallow = shallow
        # if repo_url is local path, use it directly
        if repo_url.startswith("file://"):
            self.local_path = Path(repo_url[7:])
        elif Path(repo_url).exists():
            self.local_path = Path(repo_url)
        elif local_path:
            self.local_path = Path(local_path)
        else:
            # temp clone path — cross-platform via tempfile.gettempdir()
            import tempfile

            h = hashlib.md5(repo_url.encode(), usedforsecurity=False).hexdigest()[:8]
            self.local_path = Path(tempfile.gettempdir()) / f"pkh_git_{h}"
        self._file_cache: dict[str, RawItem] = {}

    async def connect(self) -> None:
        if self.local_path.exists() and (self.local_path / ".git").exists():
            try:
                await _run(["git", "pull", "origin", self.branch], cwd=self.local_path)
                logger.info(f"Pulled {self.repo_url} branch {self.branch}")
            except Exception as e:
                logger.warning(f"git pull failed: {e}")
        elif self.local_path.exists():
            # local dir without .git - treat as already present source
            logger.info(f"Using local path {self.local_path}")
        else:
            # clone
            if self.repo_url.startswith("http") or self.repo_url.startswith("git@"):
                cmd = ["git", "clone", "--branch", self.branch]
                if self.shallow:
                    cmd.extend(["--depth", "1"])
                cmd.extend([self.repo_url, str(self.local_path)])
                await _run(cmd)
                logger.info(f"Cloned {self.repo_url} -> {self.local_path}")
            else:
                raise SourceError(f"Cannot clone local path that does not exist: {self.repo_url}")

    async def disconnect(self) -> None:
        pass

    def _is_git_repo(self) -> bool:
        return (self.local_path / ".git").exists()

    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        items: list[RawItem] = []
        if not self.local_path.exists():
            return items
        # use git ls-files if git repo, else walk filesystem
        files: list[Path] = []
        if self._is_git_repo():
            try:
                out = await _run(
                    ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                    cwd=self.local_path,
                )
                files = [self.local_path / f for f in out.splitlines() if f.strip()]
            except Exception:
                out = await _run(["git", "ls-files"], cwd=self.local_path)
                files = [self.local_path / f for f in out.splitlines() if f.strip()]
        else:
            files = await asyncio.to_thread(
                lambda: [
                    p for p in self.local_path.rglob("*") if p.is_file() and ".git" not in p.parts
                ]
            )

        for f in files:
            # skip cache/build artifacts; only skip well-known dirs, not any dotfile
            parts = set(f.parts)
            if (
                ".git" in parts
                or "__pycache__" in parts
                or ".venv" in parts
                or "node_modules" in parts
            ):
                continue
            if f.name.startswith(".") and f.name not in (".gitignore",):
                # skip hidden files like .env but keep .gitignore docs
                if f.suffix == "":
                    continue
            if "__pycache__" in str(f) or ".pyc" in f.suffix:
                continue
            stat = await asyncio.to_thread(f.stat)
            if stat.st_size > 5_000_000:
                continue
            # skip non-text binary by extension
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".pyc"):
                # for now allow md/pdf but treat pdf as skip if binary
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz"):
                    continue
            try:
                content = await asyncio.to_thread(f.read_text, encoding="utf-8", errors="ignore")
                if not content.strip():
                    continue
            except Exception:
                continue
            rel = str(f.relative_to(self.local_path))
            ext = f.suffix.lower()
            lang = EXT_LANG_MAP.get(ext, "text")
            # try to get last commit info + commit time (avoid now() skew)
            commit_hash = ""
            commit_time: datetime | None = None
            if self._is_git_repo():
                try:
                    commit_hash = await _run(
                        ["git", "log", "-1", "--format=%H", "--", rel], cwd=self.local_path
                    )
                except Exception:
                    commit_hash = ""
                try:
                    ts = await _run(
                        ["git", "log", "-1", "--format=%ct", "--", rel], cwd=self.local_path
                    )
                    if ts.strip().isdigit():
                        commit_time = datetime.fromtimestamp(int(ts.strip()), tz=timezone.utc)
                except Exception:
                    commit_time = None
            if commit_time is None:
                try:
                    commit_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                except Exception:
                    commit_time = datetime.now(timezone.utc)
            items.append(
                RawItem(
                    item_id=rel,
                    source_type=SourceType.GIT.value,
                    title=rel,
                    content=content,
                    content_type=lang,
                    metadata={
                        "file_path": rel,
                        "language": lang,
                        "size_bytes": len(content.encode()),
                        "commit_hash": commit_hash,
                        "repo_url": self.repo_url,
                    },
                    updated_at=commit_time,
                )
            )
        # populate single-item cache for O(1) get_item
        self._file_cache = {it.item_id: it for it in items}
        return items

    async def get_item(self, item_id: str) -> RawItem:
        # O(1) via cache; single-file read fallback (avoid full list_items scan)
        if item_id in self._file_cache:
            return self._file_cache[item_id]
        f = self.local_path / item_id
        if f.is_file():
            try:
                content = await asyncio.to_thread(f.read_text, encoding="utf-8", errors="ignore")
                ext = f.suffix.lower()
                return RawItem(
                    item_id=item_id,
                    source_type=SourceType.GIT.value,
                    title=item_id,
                    content=content,
                    content_type=EXT_LANG_MAP.get(ext, "text"),
                    metadata={"file_path": item_id, "repo_url": self.repo_url},
                    updated_at=datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc),
                )
            except Exception as e:
                raise SourceError(f"cannot read item {item_id}: {e}") from e
        items = await self.list_items()
        for it in items:
            if it.item_id == item_id:
                return it
        raise SourceError(f"item not found: {item_id}")

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        if not self._is_git_repo():
            # incremental via mtime filter (not full return-all)
            all_items = await self.list_items()
            result = []
            for it in all_items:
                try:
                    p = self.local_path / it.item_id
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                    if mtime > since:
                        result.append(it)
                except Exception:
                    continue
            return result
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        try:
            out = await _run(
                ["git", "log", f"--since={since_str}", "--name-only", "--pretty=format:"],
                cwd=self.local_path,
            )
            changed = {line.strip() for line in out.splitlines() if line.strip()}
            all_items = await self.list_items()
            return [it for it in all_items if it.item_id in changed]
        except Exception:
            return []

    def health_check(self) -> bool:
        return self.local_path.exists()

    # sync helper to get file hash for change detection
    def content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()
