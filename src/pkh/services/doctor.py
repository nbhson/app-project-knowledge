"""Environment health checks (`pkh doctor`).

Round 2 feature: one command that verifies the deployment is sane — settings
resolution, storage paths, git availability, audit chain integrity, provider
configuration — and reports PASS/WARN/FAIL per check with an actionable fix
hint. Exit code 1 when any check FAILs.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from pkh.config.settings import Settings, get_settings
from pkh.governance.audit import AuditLog
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CheckResult:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    detail: str
    fix: str = ""


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)
    settings_source: str = ""

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c.status == "WARN")


def _writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return os.access(path, os.W_OK)


def _config_source() -> str:
    env = os.getenv("PKH_CONFIG_FILE")
    if env:
        return f"env PKH_CONFIG_FILE={env}"
    for c in (Path("config/settings.yaml"), Path("config.yaml"), Path("./settings.yaml")):
        if c.exists():
            return str(c)
    return "defaults (no YAML found)"


def _check_settings(report: DoctorReport) -> Settings | None:
    try:
        settings = get_settings()
    except Exception as e:
        report.checks.append(
            CheckResult(
                "config",
                "FAIL",
                f"settings failed to load: {e}",
                "fix the YAML / PKH_* env variables reported above; "
                "validate with: PKH_LOG_LEVEL=WARNING pkh doctor --verbose",
            )
        )
        return None
    report.checks.append(CheckResult("config", "PASS", f"settings loaded from {_config_source()}"))
    return settings


def _check_storage(settings: Settings, report: DoctorReport) -> None:
    paths: dict[str, Path] = {
        "sqlite db": Path(settings.storage.metadata.sqlite_path),
        "vector store": Path(settings.storage.vector.path),
        "graph store": Path(settings.storage.graph.persist_path),
    }
    for name, p in paths.items():
        target = p if p.suffix else p  # dirs (chroma) vs files (db/json)
        if _writable_dir(target.parent):
            report.checks.append(
                CheckResult(f"storage:{name}", "PASS", f"{target} (parent writable)")
            )
        else:
            report.checks.append(
                CheckResult(
                    f"storage:{name}",
                    "FAIL",
                    f"parent dir not writable: {target.parent}",
                    f"create/permission the directory: mkdir -p {target.parent}",
                )
            )


def _check_git(report: DoctorReport) -> None:
    git = shutil.which("git")
    if git:
        report.checks.append(CheckResult("git", "PASS", git))
    else:
        report.checks.append(
            CheckResult(
                "git",
                "WARN",
                "git binary not found in PATH",
                "git sources will fail until git is installed",
            )
        )


def _check_audit(report: DoctorReport) -> None:
    audit = AuditLog()
    if not audit.path.exists():
        report.checks.append(CheckResult("audit", "WARN", f"no audit log yet at {audit.path}"))
        return
    try:
        ok = audit.verify_chain()
    except Exception as e:
        report.checks.append(CheckResult("audit", "FAIL", f"verify_chain crashed: {e}"))
        return
    if ok:
        report.checks.append(CheckResult("audit", "PASS", f"hash chain intact ({audit.path})"))
    else:
        report.checks.append(
            CheckResult(
                "audit",
                "FAIL",
                "audit hash chain broken",
                "investigate tampering/corruption before trusting history",
            )
        )


def _check_providers(settings: Settings, report: DoctorReport) -> None:
    n_custom = len(settings.adapters.providers)
    has_key = any(
        p.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("PKH_CUSTOM_API_KEY")
        for p in settings.adapters.providers.values()
    ) or bool(
        settings.adapters.custom_api_key
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("PKH_CUSTOM_API_KEY")
    )
    detail = (
        f"default={settings.adapters.default}, custom providers={n_custom}, "
        f"api key={'set' if has_key else 'missing'}"
    )
    if settings.adapters.default == "mock":
        report.checks.append(
            CheckResult(
                "providers",
                "WARN",
                detail,
                "default adapter is 'mock' — set adapters.default in settings for real answers",
            )
        )
    elif settings.adapters.default not in ("mock", "claude", "gpt", "gemini", "local") and not (
        settings.adapters.providers or settings.adapters.custom_base_url
    ):
        report.checks.append(
            CheckResult(
                "providers",
                "FAIL",
                detail,
                f"adapter '{settings.adapters.default}' is neither builtin nor configured "
                "in adapters.providers / adapters.custom_*",
            )
        )
    else:
        report.checks.append(CheckResult("providers", "PASS", detail))


def run_doctor(settings: Settings | None = None) -> DoctorReport:
    """Run all checks and return the report (never raises for check failures)."""
    report = DoctorReport()
    resolved = _check_settings(report) if settings is None else settings
    if resolved is not None:
        report.settings_source = _config_source()
        _check_storage(resolved, report)
        _check_providers(resolved, report)
    _check_git(report)
    _check_audit(report)
    return report
