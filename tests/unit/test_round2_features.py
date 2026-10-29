"""Round 2 feature tests: export service, doctor, CLI export/doctor, logging modes."""

import io
import json
import logging

import pytest
from typer.testing import CliRunner

from pkh.cli.main import app
from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    LifecycleState,
    ObjectType,
    SourceReference,
    SourceType,
)
from pkh.services.doctor import run_doctor
from pkh.services.export import EXPORT_FORMATS, render_export
from pkh.utils.exceptions import ConfigurationError
from pkh.utils.logging import ConsoleFormatter, setup_logging

runner = CliRunner()


def _ko(
    title: str = "Sample KO", lifecycle: LifecycleState = LifecycleState.ACTIVE
) -> KnowledgeObject:
    return KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.DOCUMENT,
        title=title,
        content="some content with | pipes | and\nnewlines",
        description="a description",
        confidence=0.8,
        lifecycle_state=lifecycle,
        tags=["alpha", "beta"],
        source_references=[
            SourceReference(source_type=SourceType.GIT, source_id="README.md", url=None)
        ],
    )


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Isolate tests from the process-wide get_settings() singleton."""
    from pkh.config.settings import reset_settings

    reset_settings()
    yield
    reset_settings()


class TestExportService:
    def test_json_roundtrip(self):
        ko = _ko()
        buf = io.StringIO()
        render_export([ko], "json", buf)
        data = json.loads(buf.getvalue())
        assert data[0]["title"] == "Sample KO"
        assert data[0]["lifecycle_state"] == "ACTIVE"

    def test_csv_columns_and_flattening(self):
        buf = io.StringIO()
        render_export([_ko()], "csv", buf)
        lines = buf.getvalue().splitlines()
        assert lines[0].startswith("id,title,object_type")
        assert "Sample KO" in lines[1]
        assert "alpha,beta" in lines[1]
        # no unescaped content column issues: content excluded from csv
        assert "some content with" not in buf.getvalue()

    def test_markdown_escapes_pipes(self):
        ko = _ko(title="Sample | KO")
        buf = io.StringIO()
        render_export([ko], "markdown", buf)
        out = buf.getvalue()
        assert "# PKH Knowledge Export" in out
        assert "Objects: 1" in out
        # pipe in title must not break the summary table
        assert "Sample \\| KO" in out

    def test_unknown_format_raises(self):
        with pytest.raises(ConfigurationError, match="unknown export format"):
            render_export([_ko()], "yaml", io.StringIO())

    def test_format_normalization(self):
        buf = io.StringIO()
        render_export([_ko()], " JSON ", buf)
        assert json.loads(buf.getvalue())[0]["title"] == "Sample KO"

    def test_export_formats_tuple(self):
        assert EXPORT_FORMATS == ("json", "csv", "markdown")


class TestDoctorService:
    def test_run_doctor_returns_report(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "d.db"))
        monkeypatch.setenv("PKH_STORAGE__VECTOR__PATH", str(tmp_path / "vec"))
        monkeypatch.setenv("PKH_STORAGE__GRAPH__PERSIST_PATH", str(tmp_path / "g.json"))
        report = run_doctor()
        names = {c.name for c in report.checks}
        assert {"config", "storage:sqlite db", "providers", "git", "audit"} <= names
        assert report.failed == 0  # tmp paths writable, defaults sane

    def test_doctor_counts(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "d.db"))
        report = run_doctor()
        assert report.failed + report.warned <= len(report.checks)
        # mock default adapter is expected to warn in test env
        assert any(c.status == "WARN" for c in report.checks)


def _seed_store(tmp_path, monkeypatch) -> None:
    """Point settings at tmp paths and persist one KO so CLI commands see data."""
    import asyncio

    from pkh.config.settings import reset_settings
    from pkh.storage.unified import KnowledgeStore

    # get_settings() caches per (yaml_path, PKH_CONFIG_FILE); prior tests in the
    # same process may have cached other env-based settings — reset first.
    reset_settings()
    monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "e.db"))
    monkeypatch.setenv("PKH_STORAGE__VECTOR__PATH", str(tmp_path / "vec"))
    monkeypatch.setenv("PKH_STORAGE__GRAPH__PERSIST_PATH", str(tmp_path / "g.json"))
    store = KnowledgeStore(
        metadata_path=str(tmp_path / "e.db"),
        vector_path=str(tmp_path / "vec"),
        graph_path=str(tmp_path / "g.json"),
    )
    asyncio.run(store.save([_ko()]))


class TestCliExport:
    def test_export_stdout_csv(self, tmp_path, monkeypatch):
        _seed_store(tmp_path, monkeypatch)
        result = runner.invoke(app, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "id,title" in result.output
        assert "Sample KO" in result.output

    def test_export_stdout_csv_empty_store(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "empty.db"))
        result = runner.invoke(app, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "No knowledge objects matched" in result.output

    def test_export_bad_format_exit_2(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "e.db"))
        result = runner.invoke(app, ["export", "--format", "yaml"])
        assert result.exit_code == 2
        assert "Unknown format" in result.output

    def test_export_bad_lifecycle_exit_2(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "e.db"))
        result = runner.invoke(app, ["export", "--lifecycle", "NOPE"])
        assert result.exit_code == 2
        assert "unknown lifecycle" in result.output


class TestCliDoctor:
    def test_doctor_exit_ok(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "d.db"))
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Doctor" in result.output

    def test_doctor_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "d.db"))
        result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["failed"] == 0
        assert len(payload["checks"]) >= 5


class TestLoggingModes:
    def test_console_formatter_layout(self):
        record = logging.LogRecord(
            "pkh.test", logging.INFO, __file__, 1, "hello %s", ("world",), None
        )
        line = ConsoleFormatter().format(record)
        assert "info" in line
        assert "hello world" in line
        # single-line for non-exception records
        assert "\n" not in line

    def test_console_formatter_includes_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "pkh.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
            )
        out = ConsoleFormatter().format(record)
        assert "boom" in out

    def test_setup_logging_verbose_wins(self, monkeypatch):
        monkeypatch.setenv("PKH_LOG_LEVEL", "WARNING")
        try:
            setup_logging(verbose=True)
            assert logging.getLogger().level == logging.DEBUG
            setup_logging(quiet=True)
            assert logging.getLogger().level == logging.WARNING
        finally:
            setup_logging()

    def test_setup_logging_env_level(self, monkeypatch):
        monkeypatch.setenv("PKH_LOG_LEVEL", "ERROR")
        try:
            setup_logging()
            assert logging.getLogger().level == logging.ERROR
        finally:
            setup_logging()

    def test_setup_logging_unknown_fmt_falls_back_to_json(self):
        # must not raise; JSONFormatter is the safe default
        setup_logging(fmt="not-a-format")
        assert logging.getLogger().level == logging.INFO
