"""E2E test: ingest -> query -> context."""

import pytest
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.storage.unified import KnowledgeStore
from pkh.engines.retrieval.intent import classify_intent
from pkh.engines.retrieval.retriever import HybridRetriever
from pkh.engines.retrieval.reranker import rerank, deduplicate
from pkh.engines.context_delivery.assembler import ContextAssembler
from pkh.engines.context_delivery.compressor import compress
from pkh.adapters import get_adapter
from pkh.models.knowledge import LifecycleState


@pytest.mark.asyncio
async def test_e2e_ingest_query(sample_git_repo, tmp_path):
    store = KnowledgeStore(metadata_path=str(tmp_path / "db.db"), vector_path=str(tmp_path / "chroma"), graph_path=str(tmp_path / "graph.json"))

    conn = GitConnector(repo_url=str(sample_git_repo))
    mgr = SyncManager([conn])
    items = await mgr.collect_all()
    assert len(items) >= 2

    pipeline = ExtractionPipeline(llm_enabled=False)
    kos, stats = await pipeline.run(items)
    assert len(kos) >= 2

    for ko in kos:
        if ko.lifecycle_state == LifecycleState.DISCOVERED:
            ko.lifecycle_state = LifecycleState.ACTIVE

    await store.save(kos)

    # query
    retriever = HybridRetriever(store)
    fused, _ = await retriever.retrieve("PaymentService", top_k=5)
    assert len(fused) >= 1

    fused = deduplicate(fused)
    fused = rerank(fused)

    assembler = ContextAssembler(store)
    intent = classify_intent("How does PaymentService work?")
    pkg = await assembler.assemble("How does PaymentService work?", fused[:3], intent=intent)
    pkg = compress(pkg)

    assert len(pkg.knowledge) >= 1
    assert any("Payment" in k.title for k in pkg.knowledge)

    adapter = get_adapter("mock")
    answer = await adapter.complete(pkg)
    assert "PaymentService" in answer or "payment" in answer.lower()
    # source traceability
    assert len(pkg.sources) >= 1
    for chunk in pkg.knowledge:
        assert len(chunk.sources) >= 1
