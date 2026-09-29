"""Tests for custom OpenAI-compatible provider (no mock)."""

from __future__ import annotations

import pytest

from pkh.adapters import get_adapter
from pkh.adapters.custom import OpenAICompatibleAdapter
from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats
from pkh.models.knowledge import SourceReference, SourceType
from pkh.utils.exceptions import AdapterError, ConfigurationError


def _pkg():
    sr = SourceReference(source_type=SourceType.GIT, source_id="s")
    chunk = KnowledgeChunk(
        id="1",
        type="FILE",
        title="T",
        content="hello",
        confidence=0.9,
        lifecycle_state="ACTIVE",
        relevance_score=1.0,
        rank=1,
        sources=[sr],
    )
    return ContextPackage(
        query="q",
        knowledge=[chunk],
        relationships=[],
        confidence=0.9,
        sources=[sr],
        lifecycle_states=["ACTIVE"],
        search_stats=SearchStats(),
    )


class _Resp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = str(data)[:500]

    def json(self):
        return self._data


class _FakeClient:
    instances: list = []

    def __init__(self, response, **kwargs):
        self._response = response
        self.kwargs = kwargs
        self.posts: list = []
        _FakeClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.posts.append({"url": url, "json": json, "headers": headers})
        return self._response


def _patch(monkeypatch, response, **kwargs):
    import httpx

    def _factory(**kw):
        return _FakeClient(response, **{**kwargs, **kw})

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_complete_success(monkeypatch):
    _FakeClient.instances.clear()
    _patch(monkeypatch, _Resp({"choices": [{"message": {"content": "hello answer"}}]}))
    a = OpenAICompatibleAdapter(base_url="https://llm.example/v1", model="m1", api_key="k")
    out = await a.complete(_pkg())
    assert out == "hello answer"
    post = _FakeClient.instances[-1].posts[0]
    assert post["url"] == "https://llm.example/v1/chat/completions"
    assert post["json"]["model"] == "m1"
    assert post["headers"]["Authorization"] == "Bearer k"


@pytest.mark.asyncio
async def test_complete_http_error(monkeypatch):
    _patch(monkeypatch, _Resp({"error": "x"}, status=500))
    a = OpenAICompatibleAdapter(base_url="https://llm.example/v1", model="m1")
    with pytest.raises(AdapterError):
        await a.complete(_pkg())


@pytest.mark.asyncio
async def test_complete_bad_payload(monkeypatch):
    _patch(monkeypatch, _Resp({"choices": []}))
    a = OpenAICompatibleAdapter(base_url="https://llm.example/v1", model="m1")
    with pytest.raises(AdapterError):
        await a.complete(_pkg())


def test_missing_config_raises():
    import asyncio as aio

    a = OpenAICompatibleAdapter(base_url="", model="")
    with pytest.raises(ConfigurationError):
        aio.run(a.complete(_pkg()))


@pytest.mark.asyncio
async def test_embed_success(monkeypatch):
    _patch(
        monkeypatch,
        _Resp({"data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3]}]}),
    )
    a = OpenAICompatibleAdapter(
        base_url="https://llm.example/v1", model="m1", embedding_model="emb"
    )
    vecs = await a.embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3]]


@pytest.mark.asyncio
async def test_embed_missing_model():
    a = OpenAICompatibleAdapter(base_url="https://llm.example/v1", model="m1")
    with pytest.raises(ConfigurationError):
        await a.embed(["a"])


def test_factory_custom_and_named_provider(tmp_path, monkeypatch):
    from pkh.config.settings import reset_settings

    y = tmp_path / "s.yaml"
    y.write_text(
        "adapters:\n"
        "  default: myprov\n"
        "  providers:\n"
        "    myprov:\n"
        '      base_url: "https://llm.example/v1"\n'
        '      model: "mx"\n'
        "      timeout_seconds: 30\n"
    )
    reset_settings()
    monkeypatch.setenv("PKH_CONFIG_FILE", str(y))
    try:
        a = get_adapter("myprov")
        assert isinstance(a, OpenAICompatibleAdapter)
        assert a.model == "mx"
        b = get_adapter("provider:myprov")
        assert isinstance(b, OpenAICompatibleAdapter)
        c = get_adapter("custom", base_url="https://o/v1", model="mm", api_key="kk")
        assert c.base_url == "https://o/v1"
        assert c.model == "mm"
    finally:
        monkeypatch.delenv("PKH_CONFIG_FILE", raising=False)
        reset_settings()


def test_factory_builtin_still_works():
    assert get_adapter("mock").__class__.__name__ == "MockAdapter"
