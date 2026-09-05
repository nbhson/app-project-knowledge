import pytest
from pkh.models.knowledge import KnowledgeObject, SourceReference, EntityType, ObjectType, SourceType
from pkh.models.lifecycle import can_transition, transition, LifecycleState
from pkh.utils.exceptions import LifecycleError


def test_knowledge_object_valid():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc", url="http://example.com")
    ko = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="test", content="hello", source_references=[sr])
    assert ko.title == "test"
    assert ko.confidence == 0.5


def test_rejects_empty_source_refs():
    with pytest.raises(Exception):
        KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="t", content="c", source_references=[])


def test_rejects_confidence_out_of_range():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    with pytest.raises(Exception):
        KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="t", content="c", source_references=[sr], confidence=1.5)


def test_rejects_empty_content():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    with pytest.raises(Exception):
        KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="t", content="  ", source_references=[sr])


def test_entity_type_required():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    with pytest.raises(Exception):
        KnowledgeObject(object_type=ObjectType.ENTITY, title="t", content="c", source_references=[sr])


def test_lifecycle_valid():
    assert can_transition(LifecycleState.DISCOVERED, LifecycleState.EXTRACTED)
    assert not can_transition(LifecycleState.DISCOVERED, LifecycleState.ACTIVE)


def test_lifecycle_transition():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    ko = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="t", content="c", source_references=[sr], lifecycle_state=LifecycleState.DISCOVERED)
    ko2 = transition(ko, LifecycleState.EXTRACTED, reason="test")
    assert ko2.lifecycle_state == LifecycleState.EXTRACTED


def test_invalid_transition_raises():
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc")
    ko = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.FILE, title="t", content="c", source_references=[sr], lifecycle_state=LifecycleState.DISCOVERED)
    with pytest.raises(LifecycleError):
        transition(ko, LifecycleState.ACTIVE)
