"""Audit logging with hash chain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class AuditLog:
    def __init__(self, path: str = "./data/audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        try:
            lines = self.path.read_text().strip().splitlines()
            if not lines:
                return "0" * 64
            last = json.loads(lines[-1])
            return last.get("hash", "0" * 64)
        except Exception:
            return "0" * 64

    def log(
        self,
        action: str,
        actor: str = "system",
        resource: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict:
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
        logger.info(f"Audit: {action} by {actor} on {resource}")
        return entry

    def list(self, limit: int = 100) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text().strip().splitlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        return entries[-limit:]

    def verify_chain(self) -> bool:
        if not self.path.exists():
            return True
        lines = self.path.read_text().strip().splitlines()
        prev = "0" * 64
        for line in lines:
            entry = json.loads(line)
            h = entry.pop("hash")
            payload = json.dumps(entry, sort_keys=True)
            expected = hashlib.sha256((prev + payload).encode()).hexdigest()
            if h != expected:
                return False
            prev = h
        return True
