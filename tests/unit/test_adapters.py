import pytest
from pkh.adapters import get_adapter
from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats
from pkh.models.knowledge import SourceReference, SourceType


@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = get_adapter("mock")
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc", url="http://example.com")
    chunk = KnowledgeChunk(id="1", type="CLASS", title="PaymentService", content="Handles payments", confidence=0.9, lifecycle_state="ACTIVE", relevance_score=0.9, rank=1, sources=[sr])
    pkg = ContextPackage(query="How does PaymentService work?", knowledge=[chunk], relationships=[], confidence=0.9, sources=[sr], lifecycle_states=["ACTIVE"], search_stats=SearchStats())
    text = adapter.format_context(pkg)
    assert "PaymentService" in text
    ans = await adapter.complete(pkg)
    assert "PaymentService" in ans


def test_get_adapter_types():
    for name in ["mock", "claude", "openai", "gemini", "local"]:
        a = get_adapter(name)
        assert a is not None
        assert a.get_token_limit() > 0
