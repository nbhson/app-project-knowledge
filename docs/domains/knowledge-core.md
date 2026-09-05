# Knowledge Core Domain

> Domain 2: Store and maintain the canonical memory of the project.
> Implements Engine 4.
> [[glossary]]

---

## Responsibility

The Knowledge Core domain is the heart of the system. It persists all knowledge in multiple storage layers, maintains the semantic model (entities, relationships, lifecycle), ensures data integrity and source traceability, and serves as the single source of truth for all queries.

### Core Responsibilities

1. **Persist** all knowledge across Vector, Graph, Metadata, and Raw Sources layers
2. **Maintain** the Knowledge Model (entity types, relationship types, lifecycle states)
3. **Ensure** data integrity: every KnowledgeObject is valid and traceable
4. **Serve** as the queryable foundation for Domains 3 and 4
5. **Preserve** original source data for audit and re-processing

---

## Engine in This Domain

| Engine | Role | Key Output |
|--------|------|------------|
| **4. Knowledge Storage** | Persist across layers | Knowledge + metadata + sources in all 4 layers |

---

## Storage Layers

| Layer | Technology (Dev) | Technology (Prod) | Purpose | Query Pattern | Index |
|-------|------------------|-------------------|---------|---------------|-------|
| **Vector Store** | ChromaDB | pgvector / Weaviate / Qdrant | Semantic similarity search | "Find knowledge about X" | Embedding vector |
| **Graph Store** | NetworkX (in-memory) | Neo4j / Neptune | Relationship traversal | "What depends on X?" | Node ID + edge list |
| **Metadata Store** | SQLite | PostgreSQL | Structured filtering & traceability | "Find ACTIVE knowledge from Jira PROJ" | B-tree on (lifecycle_state, entity_type, tags) |
| **Raw Sources** | Local filesystem | S3 / GCS | Original data preservation | "Show me the source" | Object key (source_type + source_id) |

---

## Data Integrity Rules

### Inbound (from Domain 1)
```
KnowledgeObject arrives
    |
    v
Validate: entity_type in Entity Taxonomy?  --> NO: reject, log
    |
    v
Validate: lifecycle_state is valid transition?  --> NO: reject, log
    |
    v
Validate: source_references is non-empty?  --> NO: reject, log
    |
    v
Validate: confidence is 0.0-1.0?  --> NO: default to 0.5
    |
    v
Write to ALL layers (transactional)
    |
    v
Acknowledge success / Rollback on failure
```

### Cross-Layer Consistency
- All writes happen in a single transaction
- If any layer fails, ALL writes are rolled back
- Periodic consistency check: verify vector IDs exist in metadata store, graph nodes exist in metadata store

---

## Knowledge Model Host

This domain hosts and enforces the Knowledge Model:

| Model Component | Stored Where | Enforced By |
|-----------------|--------------|-------------|
| **Entity Taxonomy** | Metadata Store (lookup table) | Validation on write |
| **Relationship Taxonomy** | Metadata Store (lookup table) | Validation on write |
| **Lifecycle States** | Metadata Store (state machine) | Validation on write + update loop |
| **SourceReferences** | Metadata Store (join table) | Validation on write |

---

## API Surface (Internal)

```python
class KnowledgeCore:
    """The central knowledge persistence and query layer."""
    
    # Write operations (called by Engine 4 / Storage Engine)
    async def write(self, knowledge: list[KnowledgeObject]) -> WriteResult
    async def update(self, knowledge: KnowledgeObject) -> None
    async def delete(self, id: str) -> None
    
    # Read operations (called by Engine 5 / Retrieval Engine)
    async def get(self, id: str) -> KnowledgeObject | None
    async def query(self, filters: dict, limit: int) -> list[KnowledgeObject]
    async def get_source_references(self, knowledge_id: str) -> list[SourceReference]
    
    # Health & metrics
    async def health_check(self) -> HealthStatus
    async def get_stats(self) -> CoreStats
```

---

## Error Handling

| Error Type | Recovery |
|------------|----------|
| Vector store connection lost | Retry with backoff; queue writes |
| Graph store corruption | Rebuild from Metadata Store + Raw Sources |
| Database lock contention | Retry with exponential backoff |
| Disk full | Alert admin; pause writes; clear old ARCHIVED data |
| Inconsistent cross-layer data | Trigger re-sync from Raw Sources |