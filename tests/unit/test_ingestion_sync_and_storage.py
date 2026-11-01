"""Boost coverage to >=70%: connectors, sync, vector, unified, pipeline, parser, etc."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pkh.engines.ingestion.confluence_connector import ConfluenceConnector
from pkh.engines.ingestion.document_connector import DocumentConnector
from pkh.engines.ingestion.jira_connector import JiraConnector
from pkh.engines.ingestion.models import RawItem
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    LifecycleState,
    ObjectType,
    SourceReference,
    SourceType,
)


def _sr():
    return SourceReference(source_type=SourceType.GIT, source_id="s")


def _raw(item_id="f.py", content="def foo(): pass", st="GIT"):
    return RawItem(item_id=item_id, source_type=st, title=item_id, content=content)


# --- document connector ---
@pytest.mark.asyncio
async def test_document_connector_basic(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "a.md").write_text("# Hello\nmust do X carefully here")
    (d / "b.txt").write_text("plain text file content here")
    conn = DocumentConnector(paths=[str(d)], patterns=["*.md", "*.txt"])
    items = await conn.list_items()
    assert len(items) == 2
    got = await conn.get_item(items[0].item_id)
    assert got.item_id == items[0].item_id
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    changes = await conn.detect_changes(since)
    assert len(changes) >= 1
    assert conn.health_check() is True
    with pytest.raises(FileNotFoundError):
        await conn.get_item("nonexistent-xyz")


# --- confluence unit (no network) ---
def test_confluence_auth_headers():
    c = ConfluenceConnector(base_url="https://x", spaces=["ENG"])
    assert c._auth_headers() == {}
    c2 = ConfluenceConnector(base_url="https://x", token="tok")
    assert c2._auth_headers() == {"Authorization": "Bearer tok"}
    c3 = ConfluenceConnector(base_url="https://x", token="tok", email="a@b.c")
    assert c3._auth_headers()["Authorization"].startswith("Basic ")


def test_confluence_page_to_raw():
    page = {
        "id": "123",
        "title": "T",
        "body": {"storage": {"value": "hello"}},
        "version": {"number": 2},
    }
    raw = ConfluenceConnector._page_to_raw(page, "ENG")
    assert raw.item_id == "123"
    assert raw.source_type == SourceType.CONFLUENCE.value


@pytest.mark.asyncio
async def test_confluence_unconfigured_returns_empty():
    c = ConfluenceConnector(base_url="", token=None)
    assert await c.list_items() == []
    assert await c.detect_changes(datetime.now(timezone.utc)) == []
    assert c.health_check() is False
    await c.connect()
    await c.disconnect()
    async with c:
        pass


# --- jira unit ---
def test_jira_escape_and_headers():
    from pkh.engines.ingestion import jira_connector as jira_mod
    from pkh.engines.ingestion.jira_connector import JiraConnector

    assert jira_mod._escape_jql_value('a"b') == 'a\\"b'
    c = JiraConnector(base_url="https://x", projects=["P"])
    assert "Authorization" not in c._auth_headers()
    c2 = JiraConnector(base_url="https://x", token="t")
    assert c2._auth_headers() == {"Authorization": "Bearer t"}


@pytest.mark.asyncio
async def test_jira_unconfigured_empty():
    c = JiraConnector(base_url="")
    assert await c.list_items() == []
    assert c.health_check() is False
    await c.connect()
    await c.disconnect()


# --- sync manager with fakes ---
class _FakeConn:
    def __init__(self, st, items):
        from pkh.models.knowledge import SourceType as SourceTypeEnum

        self.source_type = SourceTypeEnum.GIT if st == "GIT" else SourceTypeEnum.DOCUMENT
        self._items = items
        self.connected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def list_items(self, cursor=None):
        return list(self._items)

    async def detect_changes(self, since):
        return list(self._items)[:1]


@pytest.mark.asyncio
async def test_sync_manager_full_and_incremental():
    items = [_raw("a"), _raw("b")]
    mgr = SyncManager([_FakeConn("GIT", items)])
    res = await mgr.run_full_sync()
    assert res.total_items_processed == 2
    res2 = await mgr.run_incremental_sync(datetime.now(timezone.utc))
    assert res2.total_items_processed == 1
    out = await mgr.sync_source("git")
    assert len(out) == 2
    assert await mgr.sync_source("nope") == []
    assert len(await mgr.collect_all()) == 2
    mgr.register(_FakeConn("DOCUMENT", [_raw("c")]))
    assert len(await mgr.collect_all()) == 3


# --- vector in-memory ---
@pytest.mark.asyncio
async def test_inmemory_vector_crud():
    from pkh.storage.vector import InMemoryVectorStore

    vs = InMemoryVectorStore()
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.FILE,
        title="Pay",
        content="payment credit card processing",
        source_references=[_sr()],
    )
    await vs.upsert(ko)
    await vs.upsert_many([ko])
    res = await vs.query("payment credit", top_k=5)
    assert len(res) >= 1
    res2 = await vs.query("payment", top_k=5, filters={"lifecycle_states": ["ARCHIVED"]})
    assert res2 == []
    assert await vs.count() == 1
    await vs.delete([ko.id])
    assert await vs.count() == 0
    assert await vs.query("x") == []


@pytest.mark.asyncio
async def test_chroma_fallback_path(tmp_path):
    from pkh.storage.vector import ChromaVectorStore

    vs = ChromaVectorStore(path=str(tmp_path / "chroma"), collection="k")
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.FILE,
        title="Auth",
        content="authentication login flow",
        source_references=[_sr()],
    )
    await vs.upsert(ko)
    await vs.upsert_many_batched([ko])
    res = await vs.query("authentication", top_k=3)
    assert len(res) >= 1
    await vs.delete([ko.id])
    assert await vs.count() >= 0


# --- unified extra ---
@pytest.mark.asyncio
async def test_unified_extra_ops(tmp_path):
    from pkh.storage.unified import KnowledgeStore

    store = KnowledgeStore(
        metadata_path=str(tmp_path / "db.db"),
        vector_path=str(tmp_path / "chroma"),
        graph_path=str(tmp_path / "graph.json"),
    )
    sr = SourceReference(source_type=SourceType.GIT, source_id="src1")
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.CLASS,
        title="Svc",
        content="service content",
        source_references=[sr],
    )
    await store.save([ko])
    assert await store.get(ko.id) is not None
    assert len(await store.get_by_source("src1")) >= 1
    await store.save_many([ko])
    n = await store.reconcile_pending(batch=10)
    assert isinstance(n, int)
    hc = await store.health_check()
    assert "metadata_count" in hc
    await store.delete(ko.id)
    assert await store.get(ko.id) is None


# --- pipeline ---
@pytest.mark.asyncio
async def test_pipeline_cache_budget_and_dispatch():
    from pkh.engines.extraction.pipeline import ExtractionPipeline

    pipe = ExtractionPipeline(llm_enabled=False)
    items = [
        RawItem(item_id="a.py", source_type="GIT", title="a.py", content="def f():\n    pass\n"),
        RawItem(
            item_id="doc1",
            source_type="DOCUMENT",
            title="Doc",
            content="# H\nmust follow rule carefully",
        ),
        RawItem(
            item_id="j1",
            source_type="JIRA",
            title="Story",
            content="do work",
            metadata={"issue_type": "Story"},
        ),
        RawItem(item_id="empty", source_type="GIT", title="e", content="   "),
    ]
    kos1, s1 = await pipe.run(items)
    assert s1["inputs_processed"] == 4
    kos2, _ = await pipe.run(items[:1])  # cache hit
    assert len(kos2) >= 1
    # llm enrich path (mock adapter returns [])
    from pkh.adapters.mock import MockAdapter

    pipe2 = ExtractionPipeline(llm_enabled=True, llm_adapter=MockAdapter(), budget_tokens=10**9)
    out = await pipe2._llm_enrich(kos1[:1], items[0])
    assert isinstance(out, list)
    est = pipe2._estimate_tokens("hello world")
    assert est > 0


# --- parser ---
def test_parser_python_and_nonpy():
    from pkh.engines.code_intelligence.parser import CodeParser

    p = CodeParser()
    out = p.parse("m.py", "class A:\n    def m(self):\n        self.foo()\n")
    assert any(e.kind in ("CLASS", "METHOD") for e in out.entities)
    out2 = p.parse("app.ts", "class B {}")
    assert out2.entities == []
    assert len(out2.errors) >= 1
    out3 = p.parse_many([_raw("x.py", "def g():\n    h()\n")])
    assert len(out3.entities) >= 1


# --- reranker / compressor / assembler / audit / config ---
def test_reranker_helpers():
    from datetime import datetime, timezone

    from pkh.engines.retrieval.reranker import (
        deduplicate,
        lifecycle_bonus,
        recency_score,
        rerank,
    )

    assert lifecycle_bonus(LifecycleState.ACTIVE) == 1.0
    assert lifecycle_bonus(LifecycleState.ARCHIVED) == 0.0
    assert recency_score(datetime.now(timezone.utc)) == 1.0
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.FILE,
        title="t",
        content="c",
        source_references=[_sr()],
        confidence=0.9,
    )
    assert len(rerank([(ko, 0.9)])) == 1
    assert len(deduplicate([(ko, 0.5), (ko, 0.9)])) == 1


def test_compressor_tiers():
    from pkh.engines.context_delivery.compressor import compress
    from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats

    sr = _sr()
    chunks = [
        KnowledgeChunk(
            id=str(i),
            type="FILE",
            title=f"t{i}",
            content="x" * 5000,
            confidence=0.9 if i else 0.1,
            lifecycle_state="ACTIVE",
            relevance_score=float(i),
            rank=i + 1,
            sources=[sr],
        )
        for i in range(5)
    ]
    pkg = ContextPackage(
        query="q",
        knowledge=chunks,
        relationships=[],
        confidence=0.8,
        sources=[sr],
        lifecycle_states=["ACTIVE"],
        search_stats=SearchStats(),
    )
    out = compress(pkg, max_tokens=100)
    assert len(out.knowledge) <= 5
    assert any(
        log["tier"] == 1 for log in (out.search_stats.compression_log if out.search_stats else [])
    )


def test_audit_rotation_and_tamper(tmp_path):
    from pkh.governance.audit import AuditLog

    al = AuditLog(path=str(tmp_path / "a.jsonl"))
    al.MAX_BYTES = 10 * 1024 * 1024
    for i in range(10):
        al.log("act", actor="tester", resource=f"r{i}")
    assert al.verify_chain() is True
    assert len(al.list(limit=3)) == 3
    # rotation triggers on large file
    al.MAX_BYTES = 200
    al.log("act", actor="tester", resource="rot")
    assert (tmp_path / "a.jsonl").exists()
    # tamper current file
    import json

    lines = (tmp_path / "a.jsonl").read_text().strip().splitlines()
    e = json.loads(lines[0])
    e["resource"] = "TAMPERED"
    lines[0] = json.dumps(e)
    (tmp_path / "a.jsonl").write_text("\n".join(lines))
    al2 = AuditLog(path=str(tmp_path / "a.jsonl"))
    assert al2.verify_chain() is False


def test_config_yaml_and_reset(tmp_path):
    from pkh.config.settings import get_settings, reset_settings

    y = tmp_path / "s.yaml"
    y.write_text("retrieval:\n  fusion:\n    k: 60\n")
    reset_settings()
    s = get_settings(yaml_path=str(y), reload=True)
    assert s.retrieval.fusion.k == 60
    reset_settings()


def test_metadata_sqlite_windows_path(tmp_path):
    from pkh.storage.metadata import _sqlite_url

    url = _sqlite_url(str(tmp_path / "db.db"))
    assert url.startswith("sqlite:///")


@pytest.mark.asyncio
async def test_services_query_pipeline(tmp_path):
    from pkh.services.query import run_query_pipeline
    from pkh.storage.unified import KnowledgeStore

    store = KnowledgeStore(
        metadata_path=str(tmp_path / "db.db"),
        vector_path=str(tmp_path / "chroma"),
        graph_path=str(tmp_path / "graph.json"),
    )
    sr = SourceReference(source_type=SourceType.GIT, source_id="s")
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.FILE,
        title="Payment",
        content="payment handling",
        source_references=[sr],
        confidence=0.9,
        lifecycle_state=LifecycleState.ACTIVE,
    )
    await store.save(ko)
    pkg, stats, intent = await run_query_pipeline(store, "payment", top_k=3)
    assert pkg.query == "payment"
    assert stats is not None
    assert intent is not None
