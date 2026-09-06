from fastapi.testclient import TestClient


def test_health(tmp_path, monkeypatch):
    monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PKH_STORAGE__VECTOR__PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("PKH_STORAGE__GRAPH__PERSIST_PATH", str(tmp_path / "graph.json"))

    from pkh.api.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_query_flow(sample_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("PKH_STORAGE__METADATA__SQLITE_PATH", str(tmp_path / "api2.db"))
    monkeypatch.setenv("PKH_STORAGE__VECTOR__PATH", str(tmp_path / "chroma2"))
    monkeypatch.setenv("PKH_STORAGE__GRAPH__PERSIST_PATH", str(tmp_path / "graph2.json"))

    from pkh.api.main import app

    client = TestClient(app)

    # ingest
    resp = client.post("/ingest", json={"source": f"git://{sample_git_repo}"})
    assert resp.status_code == 200
    assert resp.json()["ingested"] >= 1

    # query
    resp = client.post("/query", json={"query": "How does PaymentService work?", "top_k": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "context" in data
    assert data["context"]["query"] == "How does PaymentService work?"
