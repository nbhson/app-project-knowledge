# Engine 4: Knowledge Storage Engine

> Execution Capability: Persist knowledge across multiple storage layers.
> [[glossary]]

---

## Role

Store and serve knowledge across four complementary storage layers, each optimized for different query patterns. This is the persistence backbone of the entire system.

---

## Storage Architecture

```
                    +--------------------+
                    |  Write Interface   |
                    |  (KnowledgeWriter) |
                    +--------+-----------+
                             |
            +----------------+----------------+
            |                |                |
            v                v                v
   +----------------+  +--------------+  +----------------+
   |  Vector Store  |  |  Graph Store |  |  Metadata Store|
   |  (embeddings)  |  |  (entities   |  |  (SQL/structured|
   |                |  |   + edges)   |  |   filtering)   |
   +-------+--------+  +------+-------+  +-------+--------+
           |                 |                    |
           +--------+--------+--------------------+
                    |
                    v
           +------------------+
           |   Raw Sources    |
           |   (S3 / local    |
           |    file system)  |
           +------------------+
```

---

## Storage Layers Detail

### Layer 1: Vector Store (Semantic Search)

**Purpose:** Find knowledge by semantic similarity -- "find knowledge about X" regardless of exact wording.

**Technology options:**
- Primary: `chroma` (embedded, zero-deps) for development
- Production: `pgvector` (PostgreSQL extension) or `Weaviate` / `Qdrant`

**Schema:**
```python
class VectorEntry(BaseModel):
    id: str                              # KnowledgeObject ID
    embedding: list[float]               # D-dimensional vector
    metadata: dict[str, Any]             # Filterable metadata
    content: str                         # Original text (for snippet display)
```

**Operations:**
```python
async def upsert(self, entries: list[VectorEntry]) -> None
async def search(self, query_embedding: list[float], top_k: int, filter: dict) -> list[SearchResult]
async def delete(self, ids: list[str]) -> None
```

---

### Layer 2: Graph Store (Relational Traversal)

**Purpose:** Navigate relationships between entities -- "what depends on X?", "trace from A to B".

**Technology options:**
- Primary: `networkx` (in-memory, pure Python) for development
- Production: `Neo4j` / `Amazon Neptune` / `ArangoDB`

**Schema:**
```python
class GraphNode(BaseModel):
    id: str                              # KnowledgeObject ID
    label: str                           # Entity type
    properties: dict[str, Any]           # Entity properties

class GraphEdge(BaseModel):
    source: str                          # Source node ID
    target: str                          # Target node ID
    relation: RelationshipType           # DEPENDS_ON, CALLS, etc.
    properties: dict[str, Any] = {}      # Edge metadata (confidence, etc.)
```

**Operations:**
```python
async def upsert_node(self, node: GraphNode) -> None
async def upsert_edge(self, edge: GraphEdge) -> None
async def delete_node(self, node_id: str) -> None
async def traverse(self, start_id: str, max_hops: int, relation_types: list[str]) -> GraphTraversalResult
async def find_path(self, from_id: str, to_id: str, max_hops: int) -> list[list[str]]
```

---

### Layer 3: Metadata Store (Structured Filtering)

**Purpose:** Efficient structured queries -- "find all ACTIVE knowledge from Jira project PROJ", "list all bugs with severity HIGH".

**Technology:** PostgreSQL with SQLAlchemy ORM (or SQLite for development).

**Tables:**
```sql
-- knowledge_objects
id UUID PRIMARY KEY,
object_type VARCHAR,        -- ENTITY | RELATIONSHIP | DECISION | RULE
title VARCHAR,
description TEXT,
content TEXT,
lifecycle_state VARCHAR,     -- DISCOVERED | EXTRACTED | ... | ARCHIVED
confidence FLOAT,
tags JSONB,
properties JSONB,
created_at TIMESTAMPTZ,
updated_at TIMESTAMPTZ

-- source_references
id UUID PRIMARY KEY,
knowledge_object_id UUID REFERENCES knowledge_objects(id),
source_type VARCHAR,
source_id VARCHAR,
url TEXT,
title VARCHAR,
last_synced TIMESTAMPTZ,
extra JSONB

-- sync_log
id UUID PRIMARY KEY,
source_type VARCHAR,
source_id VARCHAR,
status VARCHAR,              -- SUCCESS | FAILED
items_processed INTEGER,
duration_seconds FLOAT,
error_message TEXT,
synced_at TIMESTAMPTZ
```

**Operations:**
```python
async def insert_knowledge(self, ko: KnowledgeObject) -> str
async def update_knowledge(self, ko: KnowledgeObject) -> None
async def delete_knowledge(self, id: str) -> None
async def query(self, filters: dict, lifecycle_states: list[str], limit: int) -> list[KnowledgeObject]
async def get_by_id(self, id: str) -> KnowledgeObject | None
async def get_source_references(self, knowledge_id: str) -> list[SourceReference]
```

---

### Layer 4: Raw Sources (Original Data Preservation)

**Purpose:** Preserve original source data for audit, re-processing, and direct reference.

**Technology:** Local filesystem (development) / S3 (production).

**Operations:**
```python
async def store(self, source_type: str, source_id: str, content: bytes, metadata: dict) -> str
async def retrieve(self, storage_key: str) -> tuple[bytes, dict]
async def delete(self, storage_key: str) -> None
```

---

## Write Path

When knowledge enters from Engine 3 (Extraction), it is written to ALL layers atomically:

```python
class KnowledgeWriter:
    """Writes knowledge to all storage layers in a transaction."""
    
    async def write(self, knowledge: list[KnowledgeObject]) -> WriteResult:
        try:
            # 1. Write to Metadata Store (primary)
            ids = await self.metadata_store.insert_many(knowledge)
            
            # 2. Write to Vector Store
            embeddings = await self._embed(knowledge)
            await self.vector_store.upsert(ids, embeddings, knowledge)
            
            # 3. Write to Graph Store
            nodes, edges = await self._extract_graph(knowledge)
            await self.graph_store.upsert(nodes, edges)
            
            # 4. Write to Raw Sources
            await self.raw_store.store_batch(knowledge)
            
            return WriteResult(success=True, ids=ids)
        except Exception as e:
            # Rollback all writes
            await self._rollback(ids)
            return WriteResult(success=False, error=str(e))
```

---

## Read Path

Retrieval queries may read from one or more layers depending on the strategy:

| Query Type | Layers Read |
|------------|-------------|
| Semantic search | Vector Store |
| Relationship traversal | Graph Store |
| Structured filter | Metadata Store |
| Source lookup | Raw Sources |
| Full knowledge object | Metadata Store (primary key) |

---

## Key Design Decisions

1. **Write once, read many**: All layers are written in a single transactional batch.
2. **Source of truth preserved**: Raw sources are never modified; they are append-only.
3. **Eventual consistency**: Cross-layer consistency is achieved at write time; reads may see slightly stale data.
4. **Separate concerns**: Each layer is independently replaceable (swap pgvector for Weaviate without changing other layers).
5. **Index by lifecycle state**: Metadata Store indexes by lifecycle_state for efficient filtering during retrieval.