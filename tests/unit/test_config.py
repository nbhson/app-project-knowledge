from pkh.config.settings import Settings, get_settings


def test_settings_defaults():
    s = Settings()
    assert s.storage.vector.provider == "chroma"
    assert s.adapters.default == "mock"
    assert s.extraction.llm_enabled is False


def test_settings_from_yaml(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text("storage:\n  metadata:\n    sqlite_path: /tmp/test.db\n")
    s = Settings.from_yaml(p)
    assert s.storage.metadata.sqlite_path == "/tmp/test.db"


def test_get_settings():
    s = get_settings(reload=True)
    assert s is not None
