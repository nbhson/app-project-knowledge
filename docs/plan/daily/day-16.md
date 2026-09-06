# Day 16 — Metadata Store (SQLAlchemy + SQLite)

> **Phase:** 4 — Knowledge Storage Engine | **Date:** Day 16 of 45 | **Goal:** Implement MetadataStore for persistent knowledge storage

---

## 🎯 Daily Target

**Deliverable:** SQLAlchemy-based metadata store with full traceability

---

## ✅ Tasks

### 1. Database Schema (SQLite + SQLAlchemy)
- [ ] `knowledge_objects` table:
  - id (UUID PK), object_type, title, description, content
  - source_references (JSON), confidence (float), lifecycle_state
  - created_at, updated_at, tags (JSON), properties (JSON)
- [ ] `sources` table:
  - source_id (PK), source_type, url, title, last_synced, content_hash
- [ ] `knowledge_sources` table (junction):
  - knowledge_id, source_id (composite PK)
- [ ] `relationships` table:
  - from_id, to_id, relationship_type, confidence
- [ ] `lifecycle_events` table:
  - knowledge_id, from_state, to_state, triggered_at, trigger_reason

### 2. MetadataStore Implementation
- [ ] `MetadataStore` class with methods:
  - `save(knowledge: KnowledgeObject) -> None`
  - `get(id: str) -> KnowledgeObject | None`
  - `search(query: str, filters: dict) -> list[KnowledgeObject]`
  - `get_by_source(source_id: str) -> list[KnowledgeObject]`
  - `get_relationships(entity_id: str) -> list[Relationship]`
  - `delete(id: str) -> None`

### 3. Lifecycle Filtering
- [ ] Queries exclude DEPRECATED, ARCHIVED by default
- [ ] `get_active()` method for lifecycle-aware queries
- [ ] `update_lifecycle(id, new_state, reason)` method

### 4. Source Reference Integrity
- [ ] Foreign key constraints ensure source references exist
- [ ] Cascade handling on source deletion (update or soft-delete)

### 5. Unit Tests (`tests/unit/test_metadata_store.py`)
- [ ] Test CRUD operations
- [ ] Test search with filters
- [ ] Test lifecycle filtering
- [ ] Test relationship queries
- [ ] Test integration with KnowledgeObject model

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Schema matches specification | ☐ |
| CRUD operations work correctly | ☐ |
| Lifecycle filtering excludes DEPRECATED/ARCHIVED | ☐ |
| Source reference integrity enforced | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 17 (Vector store), Day 23 (Storage integration)
- **Blocked by:** Day 15 (Validated KnowledgeObjects)

---

## 📝 Notes

- Use SQLAlchemy 2.0 style with Declarative Base
- SQLite for development, PostgreSQL for production
- Use JSON type for source_references, tags, properties
- Commit: `feat: metadata store with sqlalchemy and lifecycle tracking`