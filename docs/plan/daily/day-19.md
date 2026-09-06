# Day 19 — Storage Integration & Unified Queries

> **Phase:** 4 — Knowledge Storage Engine | **Date:** Day 19 of 45 | **Goal:** Unified KnowledgeStore interface over all 3 stores with composite queries

---

## 🎯 Daily Target

**Deliverable:** KnowledgeStore unified interface with composite queries and performance benchmarks

---

## ✅ Tasks

### 1. KnowledgeStore Unified Interface (`unified.py`)
- [ ] `KnowledgeStore` class wrapping MetadataStore, VectorStore, GraphStore
- [ ] Methods:
  - `save(knowledge: KnowledgeObject) -> None` (writes to all 3 stores)
  - `get(id: str) -> KnowledgeObject | None`
  - `search(query: str, filters: dict) -> list[KnowledgeObject]`
  - `get_by_source(source_id: str) -> list[KnowledgeObject]`
  - `get_relationships(entity_id: str) -> list[Relationship]`
  - `delete(id: str) -> None` (deletes from all stores)
  - `composite_query(query: str, filters: dict) -> list[KnowledgeObject]`

### 2. Composite Queries
- [ ] "Find all code related to JIRA-123":
  - Graph traversal from JIRA-123 (TRACES_TO edges)
  - Filter by entity_type in [CLASS, FUNCTION, METHOD]
- [ ] "Find documents about payment":
  - Vector search for "payment" in documents
  - Filter by entity_type=DOCUMENT
- [ ] "Impact analysis: what depends on X":
  - Graph traversal: incoming DEPENDS_ON edges

### 3. Cross-Store Sync
- [ ] Metadata changes → vector store update (embeddings)
- [ ] Metadata changes → graph store update (nodes/edges)
- [ ] Event-driven sync using lifecycle events

### 4. Backup/Restore
- [ ] Export to JSON (all stores)
- [ ] Import from JSON (rebuild all stores)
- [ ] Incremental backup support

### 5. Performance Benchmarks
- [ ] Write throughput: > 1000 ops/sec
- [ ] Read latency: < 50ms single entity, < 200ms composite query
- [ ] Test with 10k+ knowledge objects

### 6. Unit Tests (`tests/unit/test_unified_store.py`)
- [ ] Test unified save/get/delete
- [ ] Test composite queries
- [ ] Test cross-store consistency
- [ ] Test backup/restore
- [ ] Benchmark performance

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Unified interface works over all 3 stores | ☐ |
| Composite queries return correct results | ☐ |
| Cross-store sync maintains consistency | ☐ |
| Backup/restore works | ☐ |
| Write throughput > 1000 ops/sec | ☐ |
| Read latency < 50ms (single), < 200ms (composite) | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Phase 5 (Retrieval engine needs storage)
- **Blocked by:** Day 16-18 (All 3 stores)

---

## 📝 Notes

- Use async/await for all store operations
- Implement connection pooling for SQLite/ChromaDB
- Transaction handling: all-or-nothing across stores
- Commit: `feat: unified knowledge store with composite queries and benchmarks`