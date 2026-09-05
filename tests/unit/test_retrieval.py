import pytest
from pkh.engines.retrieval.intent import classify_intent, IntentType
from pkh.engines.retrieval.retriever import HybridRetriever
from pkh.engines.retrieval.reranker import rerank, deduplicate
from pkh.models.knowledge import KnowledgeObject, SourceReference, EntityType, ObjectType, SourceType
from pkh.storage.unified import KnowledgeStore


def test_intent_classifier():
    assert classify_intent("How does PaymentService work?") == IntentType.CODE_UNDERSTANDING
    assert classify_intent("Why did we choose Kafka?") == IntentType.ARCHITECTURE
    assert classify_intent("What breaks if I change DB?") == IntentType.IMPACT_ANALYSIS


@pytest.mark.asyncio
async def test_retrieval_pipeline(tmp_path):
    store = KnowledgeStore(metadata_path=str(tmp_path / "db.db"), vector_path=str(tmp_path / "chroma"), graph_path=str(tmp_path / "graph.json"))
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    ko = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.CLASS, title="PaymentService", content="PaymentService handles payments via Stripe", source_references=[sr], confidence=0.9)
    await store.save(ko)
    retriever = HybridRetriever(store)
    fused, stats = await retriever.retrieve("PaymentService", top_k=5)
    assert len(fused) >= 1
    deduped = deduplicate(fused)
    reranked = rerank(deduped)
    assert len(reranked) >= 1
