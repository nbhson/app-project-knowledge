"""Audit logging with hash chain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class AuditLog:
    MAX_BYTES = 10 * 1024 * 1024  # 10MB rotation

    def __init__(self, path: str | None = None):
        # path from config if not explicitly provided
        if path is None:
            try:
                from pkh.config.settings import get_settings

                cfg_path = get_settings().governance.audit_path
                path = cfg_path
            except Exception:
                path = "./data/audit.jsonl"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.path) + ".lock")
        self._cached_hash: str | None = None
        self._cached_size: int = -1

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        try:
            size = self.path.stat().st_size
            if self._cached_hash is not None and size == self._cached_size:
                return self._cached_hash
            # read only last line (avoid O(N) full read for large logs)
            with open(self.path, "rb") as f:
                f.seek(max(0, size - 8192))
                tail = f.read().decode("utf-8", errors="ignore").strip().splitlines()
                if not tail:
                    return "0" * 64
                last = json.loads(tail[-1])
                h = last.get("hash", "0" * 64)
                self._cached_hash = h
                self._cached_size = size
                return h
        except Exception:
            return "0" * 64

    def _maybe_rotate(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size > self.MAX_BYTES:
                backup = self.path.with_suffix(".jsonl.1")
                if backup.exists():
                    backup.unlink()
                self.path.rename(backup)
                self._cached_hash = None
                self._cached_size = -1
        except Exception as e:
            logger.warning(f"Audit rotation failed: {e}")

    def log(
        self,
        action: str,
        actor: str = "system",
        resource: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict:
        # filelock around append to prevent concurrent corrupt hash chain
        with self._lock:
            self._maybe_rotate()
            prev_hash = self._last_hash()
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "actor": actor,
                "resource": resource,
                "details": details or {},
                "prev_hash": prev_hash,
            }
            payload = json.dumps(entry, sort_keys=True)
            h = hashlib.sha256((prev_hash + payload).encode()).hexdigest()
            entry["hash"] = h
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._cached_hash = h
            try:
                self._cached_size = self.path.stat().st_size
            except Exception:
                pass
            logger.info(f"Audit: {action} by {actor} on {resource}")
            return entry

    def list(self, limit: int = 100) -> list[dict]:
        if not self.path.exists():
            return []
        # Use lock for consistent read
        with self._lock:
            lines = self.path.read_text().strip().splitlines()
            entries = [json.loads(line) for line in lines if line.strip()]
            return entries[-limit:]

    def verify_chain(self) -> bool:
        if not self.path.exists():
            return True
        with self._lock:
            lines = self.path.read_text().strip().splitlines()
        prev = "0" * 64
        for line in lines:
            if not line.strip():
                continue
            entry = json.loads(line)
            # do not mutate original entry
            entry_copy = dict(entry)
            h = entry_copy.pop("hash", None)
            if h is None:
                return False
            payload = json.dumps(entry_copy, sort_keys=True)
            expected = hashlib.sha256((prev + payload).encode()).hexdigest()
            if h != expected:
                return False
            prev = h
        return True
