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

## Write Path — Consistency for Polyglot Persistence

> **Rủi ro:** 4 stores (Metadata, Vector, Graph, Raw) không có distributed transaction. Ghi hỏng giữa chừng → vector có mà graph không → query sai.

**Nguyên tắc:** Metadata Store là **source of truth** duy nhất. Vector/Graph/Raw là **derived** và có thể rebuild từ Metadata.

### Transactional Outbox Pattern (Bắt buộc)

When knowledge enters from Engine 3 (Extraction), it is written via outbox, không ghi song song 4 stores trong một try:

```python
class KnowledgeWriter:
    """Outbox pattern — Metadata là truth, các store khác là eventual consistent."""
    
    async def write(self, knowledge: list[KnowledgeObject]) -> WriteResult:
        # 1. Atomic: Metadata + outbox trong cùng DB transaction (SQLite/PostgreSQL)
        async with self.metadata_store.transaction() as tx:
            ids = await tx.insert_many(knowledge)
            await tx.insert_outbox(ids, op="UPSERT")  # bảng outbox: id, op, payload, status=PENDING
            # commit atomically — nếu fail ở đây, chưa có gì ghi ra ngoài

        # 2. Best-effort fan-out từ outbox (idempotent, retryable)
        #    Worker đọc outbox PENDING và đẩy sang Vector/Graph/Raw với idempotency_key = knowledge.id
        await self._fanout_from_outbox()  # retry 3 lần, exponential backoff

        return WriteResult(success=True, ids=ids, pending_outbox=len(ids))

    async def _fanout_from_outbox(self):
        for entry in await self.metadata_store.claim_outbox(batch=100):
            try:
                ko = await self.metadata_store.get(entry.id)
                # Idempotent upsert — ghi lại nhiều lần cho kết quả giống nhau
                await self.vector_store.upsert(ko, idempotency_key=ko.id)
                await self.graph_store.upsert(ko, idempotency_key=ko.id)
                await self.raw_store.store(ko, idempotency_key=ko.id)
                await self.metadata_store.mark_outbox_done(entry.id)
            except Exception as e:
                await self.metadata_store.mark_outbox_failed(entry.id, str(e))
                # sẽ được Reconciler retry
```

**Idempotency:** Mọi `upsert/delete` phải chấp nhận `idempotency_key` và là no-op nếu đã tồn tại cùng `content_hash`.

### Reconciliation & Repair (Bắt buộc cho Prod)

| Cơ chế | Tần suất | Việc làm |
|--------|----------|----------|
| **Outbox Reconciler** | Mỗi 1 phút | Retry các entry `FAILED` hoặc `PENDING >5m`, max 5 lần rồi alert |
| **Nightly Consistency Check** | Mỗi đêm | So sánh `count(metadata ACTIVE) vs count(vector) vs count(graph nodes)`; nếu lệch >1% → rebuild derived stores từ Metadata |
| **Read-time fallback** | Mỗi query | Nếu Vector/Graph timeout hoặc lệch, fallback về Metadata-only (vector-only) và log warning — không fail query |

### MVP Simplification

- **MVP (SQLite dev):** Chỉ cần Metadata + Vector + Graph trong cùng process, có thể dùng sequential writes + manual rollback (vì không có concurrent writer). Outbox có thể là bảng `outbox` trong SQLite như trên nhưng chạy inline thay vì background worker.
- **Prod (PostgreSQL+pgvector+Neo4j+S3):** Bắt buộc outbox worker riêng + nightly check.

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

1. **Metadata is truth, others are derived**: Vector/Graph/Raw có thể rebuild hoàn toàn từ Metadata — không bao giờ dùng vector làm truth.
2. **Outbox atomicity**: Chỉ Metadata+outbox là atomic; fan-out là eventual consistent với idempotency.
3. **Source of truth preserved**: Raw sources là append-only, không sửa.
4. **Separate concerns**: Mỗi layer thay thế được (swap pgvector ↔ Weaviate) nhưng phải implement `idempotency_key`.
5. **Index by lifecycle_state**: Metadata index `lifecycle_state` để retrieval filter nhanh; Vector/Graph cũng lưu lifecycle để filter sớm.
6. **Fail-open read**: Query không fail nếu 1 derived store chết — fallback Metadata-only và ghi `warnings` vào ContextPackage.