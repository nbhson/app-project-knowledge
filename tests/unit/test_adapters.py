import pytest

from pkh.adapters import get_adapter
from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats
from pkh.models.knowledge import SourceReference, SourceType


@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = get_adapter("mock")
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc", url="http://example.com")
    chunk = KnowledgeChunk(
        id="1",
        type="CLASS",
        title="PaymentService",
        content="Handles payments",
        confidence=0.9,
        lifecycle_state="ACTIVE",
        relevance_score=0.9,
        rank=1,
        sources=[sr],
    )
    pkg = ContextPackage(
        query="How does PaymentService work?",
        knowledge=[chunk],
        relationships=[],
        confidence=0.9,
        sources=[sr],
        lifecycle_states=["ACTIVE"],
        search_stats=SearchStats(),
    )
    text = adapter.format_context(pkg)
    assert "PaymentService" in text
    ans = await adapter.complete(pkg)
    assert "PaymentService" in ans


def test_get_adapter_types():
    for name in ["mock", "claude", "openai", "gemini", "local"]:
        a = get_adapter(name)
        assert a is not None
        assert a.get_token_limit() > 0
        # all adapters must share the same text format contract
        from pkh.engines.context_delivery.models import ContextPackage, SearchStats

        sr = SourceReference(source_type=SourceType.GIT, source_id="x")
        pkg = ContextPackage(
            query="q",
            knowledge=[],
            relationships=[],
            confidence=0.5,
            sources=[sr],
            lifecycle_states=[],
            search_stats=SearchStats(),
        )
        assert isinstance(a.format_context(pkg), str)
        assert isinstance(a.adapt(pkg), str)


@pytest.mark.asyncio
async def test_adapter_embed_consistency():
    from pkh.storage.vector import _simple_embedding

    a = get_adapter("mock")
    vecs = await a.embed(["payment service handles credit card"])
    assert len(vecs) == 1 and len(vecs[0]) == 256
    # semantic overlap: payment query closer to payment doc than auth doc
    q = _simple_embedding("payment credit card")
    p = _simple_embedding("Payment service handles credit card processing")
    au = _simple_embedding("Auth service handles authentication login")

    def cos(x, y):
        return sum(a * b for a, b in zip(x, y, strict=True))

    assert cos(q, p) > cos(q, au)
