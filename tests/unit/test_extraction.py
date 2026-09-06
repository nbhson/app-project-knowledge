import pytest

from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.models import RawItem


@pytest.mark.asyncio
async def test_extraction_pipeline_rule_based(tmp_path):
    pipeline = ExtractionPipeline(llm_enabled=False)
    items = [
        RawItem(
            item_id="test.py",
            source_type="GIT",
            title="test.py",
            content="class Foo:\n    def bar(self): pass",
            content_type="python",
        ),
        RawItem(
            item_id="doc.md",
            source_type="DOCUMENT",
            title="ADR-001",
            content="# ADR-001\nContext\nDecision\nConsequences",
            content_type="markdown",
        ),
    ]
    kos, stats = await pipeline.run(items)
    assert len(kos) >= 2
    assert stats["inputs_processed"] == 2
    assert stats["entities_extracted"] >= 1
    # ensure every KO has source_references
    for ko in kos:
        assert len(ko.source_references) >= 1
        assert 0.0 <= ko.confidence <= 1.0
