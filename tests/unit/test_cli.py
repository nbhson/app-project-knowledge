from typer.testing import CliRunner
from pkh.cli.main import app
import tempfile
from pathlib import Path

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Project Knowledge Harness" in result.output or "Usage" in result.output


def test_cli_init(tmp_path):
    result = runner.invoke(app, ["init", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "config" / "settings.yaml").exists()


def test_cli_status(tmp_path, monkeypatch):
    monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "status.db"))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


def test_cli_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "audit.db"))
    result = runner.invoke(app, ["audit"])
    assert result.exit_code == 0
