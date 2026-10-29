"""Structured JSON logging with correlation IDs."""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get() or getattr(record, "correlation_id", ""),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)
        # include extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "correlation_id",
                "message",
            ):
                log_data[key] = value
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable single-line format for interactive CLI use.

    The API and --json mode keep structured JSON output; the CLI default is
    this compact console format so terminals are not flooded with JSON noise.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S")
        level = record.levelname.lower()
        line = f"{ts} {level:<7} {record.getMessage()}"
        cid = correlation_id_var.get()
        if cid:
            line += f" [cid={cid[:8]}]"
        if record.exc_info and record.exc_info[0] is not None:
            line += "\n" + self.formatException(record.exc_info)
        return line


_FORMATTERS: dict[str, type[logging.Formatter]] = {
    "json": JSONFormatter,
    "console": ConsoleFormatter,
}


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(
    level: str | None = None,
    fmt: str = "json",
    quiet: bool = False,
    verbose: bool = False,
) -> None:
    """Configure root logging.

    - `verbose=True` -> DEBUG, `quiet=True` -> WARNING (verbose wins).
    - Otherwise `level` (falls back to env PKH_LOG_LEVEL, then INFO).
    - `fmt`: "json" (default, API) or "console" (human-readable CLI output).
    """
    resolved = "INFO"
    if verbose:
        resolved = "DEBUG"
    elif quiet:
        resolved = "WARNING"
    elif level:
        resolved = level
    else:
        resolved = os.getenv("PKH_LOG_LEVEL", "INFO")
    formatter_cls = _FORMATTERS.get(fmt.lower(), JSONFormatter)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter_cls())
    root = logging.getLogger()
    # Don't break uvicorn: avoid clearing handlers when uvicorn is running (fix-plan 3.3)
    uvicorn_logger = logging.getLogger("uvicorn")
    if uvicorn_logger.handlers:
        # uvicorn running, preserve its handlers
        if not root.handlers:
            root.addHandler(handler)
        # ensure level is set
        root.setLevel(getattr(logging, resolved.upper(), logging.INFO))
        return
    if not root.handlers:
        root.addHandler(handler)
    else:
        # safe to reset only when no uvicorn handlers present
        root.handlers.clear()
        root.addHandler(handler)
    root.setLevel(getattr(logging, resolved.upper(), logging.INFO))


def set_correlation_id(cid: str | None = None) -> str:
    cid = cid or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    return correlation_id_var.get()
