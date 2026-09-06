import pytest

from pkh.engines.context_delivery.assembler import ContextAssembler
from pkh.engines.context_delivery.compressor import compress
from pkh.engines.context_delivery.models import SearchStats
from pkh.engines.context_delivery.validator import ContextValidator
from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    ObjectType,
    SourceReference,
    SourceType,
)
from pkh.storage.unified import KnowledgeStore


@pytest.mark.asyncio
async def test_context_assembly(tmp_path):
    store = KnowledgeStore(
        metadata_path=str(tmp_path / "db.db"),
        vector_path=str(tmp_path / "chroma"),
        graph_path=str(tmp_path / "graph.json"),
    )
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc", url="http://example.com")
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.CLASS,
        title="PaymentService",
        content="Handles payments",
        source_references=[sr],
        confidence=0.9,
    )
    await store.save(ko)
    assembler = ContextAssembler(store)
    package = await assembler.assemble(
        "How does PaymentService work?",
        [(ko, 0.9)],
        intent="CODE_UNDERSTANDING",
        search_stats=SearchStats(vector_results=1),
    )
    assert package.query == "How does PaymentService work?"
    assert len(package.knowledge) == 1
    assert package.confidence > 0


def test_compression():
    from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats
    from pkh.models.knowledge import LifecycleState

    chunks = [
        KnowledgeChunk(
            id=str(i),
            type="CLASS",
            title=f"T{i}",
            content="x " * 2000,
            confidence=0.9,
            lifecycle_state=LifecycleState.ACTIVE,
            relevance_score=1.0 - i * 0.1,
            rank=i,
            sources=[],
        )
        for i in range(5)
    ]
    pkg = ContextPackage(
        query="q",
        knowledge=chunks,
        relationships=[],
        confidence=0.9,
        sources=[],
        lifecycle_states=["ACTIVE"],
        search_stats=SearchStats(),
    )
    compressed = compress(pkg, max_tokens=100)
    assert len(compressed.knowledge) < 5


def test_validator():
    from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk

    chunk = KnowledgeChunk(
        id="1",
        type="CLASS",
        title="T",
        content="hello",
        confidence=0.9,
        lifecycle_state="ACTIVE",
        relevance_score=1.0,
        rank=1,
        sources=[],
    )
    pkg = ContextPackage(
        query="q",
        knowledge=[chunk],
        relationships=[],
        confidence=0.9,
        sources=[],
        lifecycle_states=["ACTIVE"],
    )
    v = ContextValidator()
    result = v.validate(pkg)
    assert result.token_count > 0
