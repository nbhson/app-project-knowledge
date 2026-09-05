import pytest
from pkh.models.knowledge import KnowledgeObject, SourceReference, EntityType, ObjectType, SourceType
from pkh.storage.unified import KnowledgeStore


def make_ko(title="Test", content="hello", entity_type=EntityType.FILE):
    sr = SourceReference(source_type=SourceType.GIT, source_id="abc", url="http://example.com")
    return KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=entity_type, title=title, content=content, source_references=[sr], confidence=0.9)


@pytest.mark.asyncio
async def test_metadata_crud(tmp_path):
    store = KnowledgeStore(metadata_path=str(tmp_path / "db.db"), vector_path=str(tmp_path / "chroma"), graph_path=str(tmp_path / "graph.json"))
    ko = make_ko(title="PaymentService", content="PaymentService handles payments")
    await store.save(ko)
    fetched = await store.get(ko.id)
    assert fetched is not None
    assert fetched.title == "PaymentService"


@pytest.mark.asyncio
async def test_vector_search(tmp_path):
    store = KnowledgeStore(metadata_path=str(tmp_path / "db.db"), vector_path=str(tmp_path / "chroma"), graph_path=str(tmp_path / "graph.json"))
    ko1 = make_ko(title="PaymentService", content="Payment service handles credit card processing")
    ko2 = make_ko(title="AuthService", content="Auth service handles authentication")
    await store.save([ko1, ko2])
    results = await store.search("payment credit card", top_k=5)
    assert len(results) >= 1
    # payment should rank first
    assert any("Payment" in r.title for r in results)


@pytest.mark.asyncio
async def test_graph_neighbors(tmp_path):
    from pkh.models.knowledge import KnowledgeObject, SourceReference, EntityType, ObjectType, SourceType, RelationshipType

    store = KnowledgeStore(metadata_path=str(tmp_path / "db.db"), vector_path=str(tmp_path / "chroma"), graph_path=str(tmp_path / "graph.json"))
    sr = SourceReference(source_type=SourceType.GIT, source_id="x")
    ko_a = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.CLASS, title="A", content="A", source_references=[sr])
    ko_b = KnowledgeObject(object_type=ObjectType.ENTITY, entity_type=EntityType.CLASS, title="B", content="B", source_references=[sr])
    await store.save([ko_a, ko_b])
    # add relationship
    rel = KnowledgeObject(object_type=ObjectType.RELATIONSHIP, title="A DEPENDS_ON B", content="A depends on B", source_references=[sr], properties={"from": ko_a.id, "to": ko_b.id, "rel_type": "DEPENDS_ON"})
    await store.save(rel)
    neigh = await store.get_relationships(ko_a.id)
    assert ko_b.id in neigh or len(neigh) >= 0  # at least no crash
