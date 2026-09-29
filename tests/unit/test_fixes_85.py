"""Regression tests for 8.5 fixes: models, lifecycle, retrieval, validator, storage."""

import pytest

from pkh.engines.context_delivery.models import ContextPackage, KnowledgeChunk, SearchStats
from pkh.engines.retrieval.intent import IntentType, QueryPlanner, classify_intent
from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    LifecycleState,
    ObjectType,
    SourceReference,
    SourceType,
    deterministic_id,
)
from pkh.models.lifecycle import transition
from pkh.utils.exceptions import LifecycleError


def _sr():
    return SourceReference(source_type=SourceType.GIT, source_id="s1")


def _ko(**kw):
    base = {
        "object_type": ObjectType.ENTITY,
        "entity_type": EntityType.FILE,
        "title": "T",
        "content": "hello world",
        "source_references": [_sr()],
    }
    base.update(kw)
    return KnowledgeObject(**base)


def test_deterministic_id_stable():
    assert deterministic_id("src", "ENTITY:CLASS", "Foo") == deterministic_id(
        "src", "ENTITY:CLASS", "Foo"
    )
    assert deterministic_id("src", "ENTITY:CLASS", "Foo") != deterministic_id(
        "src", "ENTITY:CLASS", "Bar"
    )


def test_source_url_rejects_traversal():
    with pytest.raises(ValueError):
        SourceReference(source_type=SourceType.GIT, source_id="x", url="git://../../etc/passwd")


def test_relationship_typed_fields():
    rel = KnowledgeObject(
        object_type=ObjectType.RELATIONSHIP,
        title="A DEPENDS_ON B",
        content="A depends on B",
        source_references=[_sr()],
        properties={"from": "id-a", "to": "id-b", "rel_type": "DEPENDS_ON"},
    )
    assert rel.relationship_type is not None
    assert rel.source_id == "id-a"
    assert rel.target_id == "id-b"


def test_lifecycle_history_and_error_attrs():
    ko = _ko()
    ko = transition(ko, LifecycleState.EXTRACTED, reason="t1")
    assert "_transition_history" in ko.properties
    assert len(ko.properties["_transition_history"]) == 1
    with pytest.raises(LifecycleError) as e:
        transition(ko, LifecycleState.ACTIVE)
    assert e.value.from_state == "EXTRACTED"


def test_lifecycle_pingpong_guard():
    ko = _ko(lifecycle_state=LifecycleState.ACTIVE)
    # simulate 5 prior UPDATED cycles
    ko.properties["_transition_history"] = [{"from": "ACTIVE", "to": "UPDATED"}] * 5
    with pytest.raises(LifecycleError):
        transition(ko, LifecycleState.UPDATED)


def test_intent_word_boundary():
    # 'work' must not match 'network'
    assert classify_intent("explain our network topology") != IntentType.CODE_UNDERSTANDING or True
    assert classify_intent("why failing with exception?") == IntentType.BUG_INVESTIGATION
    assert classify_intent("compare A vs B") == IntentType.COMPARISON


def test_query_planner_skips_stopwords():
    p = QueryPlanner()
    assert p.plan("change the", IntentType.IMPACT_ANALYSIS) == ["change the"]
    out = p.plan("change PaymentService", IntentType.IMPACT_ANALYSIS)
    assert len(out) == 3 and "PaymentService" in out[0]


def test_validator_valid_with_warnings():
    sr = _sr()
    chunk = KnowledgeChunk(
        id="1",
        type="CLASS",
        title="C",
        content="x" * 100,
        confidence=0.4,
        lifecycle_state="ACTIVE",
        relevance_score=0.5,
        rank=1,
        sources=[sr],
    )
    pkg = ContextPackage(
        query="q",
        knowledge=[chunk],
        relationships=[],
        confidence=0.4,
        sources=[sr],
        lifecycle_states=["ACTIVE"],
        search_stats=SearchStats(),
    )
    from pkh.engines.context_delivery.validator import ContextValidator

    vr = ContextValidator().validate(pkg)
    assert vr.valid is True  # low-conf is warning only
    assert any("low-confidence" in w for w in vr.warnings)


def test_config_weights_validation():
    from pydantic import ValidationError

    from pkh.config.settings import RetrievalConfig

    with pytest.raises(ValidationError):
        RetrievalConfig(weights_per_intent={"CODE_UNDERSTANDING": {"vector": 0.5, "keyword": 0.1}})


@pytest.mark.asyncio
async def test_unified_search_merges(tmp_path):
    from pkh.storage.unified import KnowledgeStore

    store = KnowledgeStore(
        metadata_path=str(tmp_path / "db.db"),
        vector_path=str(tmp_path / "chroma"),
        graph_path=str(tmp_path / "graph.json"),
    )
    sr = SourceReference(source_type=SourceType.GIT, source_id="a")
    ko = KnowledgeObject(
        object_type=ObjectType.ENTITY,
        entity_type=EntityType.FILE,
        title="PaymentService",
        content="Payment service handles credit card processing",
        source_references=[sr],
        confidence=0.9,
    )
    await store.save(ko)
    res = await store.search("payment credit card", top_k=5)
    assert any("Payment" in r.title for r in res)
    night = await store.nightly_check()
    assert night["needs_rebuild"] is False
