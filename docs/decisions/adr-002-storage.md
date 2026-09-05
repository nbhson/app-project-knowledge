# ADR-002: Polyglot Persistence — Dev/Prod Split + Outbox

Date: 2026-09-06
Status: Accepted
Related: docs/engines/knowledge-storage-engine.md, docs/tech-stack.md

## Context

PKH cần 4 loại query khác nhau: semantic search, graph traversal, structured filter, raw preservation. Một DB duy nhất không tối ưu cho cả 4. Nhưng polyglot (= 4 stores) dẫn đến rủi ro sync như đã mô tả trong fix rủi ro #3.

## Decision

**Mỗi layer dùng tech best-fit, nhưng Metadata là source of truth duy nhất:**

| Layer | Dev | Prod | Lý do chọn |
|-------|-----|------|------------|
| Vector | ChromaDB (embedded) | pgvector (PostgreSQL extension) | Chroma: zero-config, embedded; pgvector: ACID, scale cùng Postgres, không cần cluster vector DB riêng |
| Graph | NetworkX (pure Python) | Neo4j 5 | NetworkX: serializable, không cần server cho MVP; Neo4j: ACID, clustering, algo phong phú |
| Metadata | SQLite + SQLAlchemy | PostgreSQL 16 | Dev zero-admin; prod enterprise, JSONB |
| Raw | Local FS | S3 / MinIO | Blob storage |

**Consistency:** Không dùng distributed transaction. Dùng **transactional outbox**: `Metadata + outbox` commit atomically, fan-out sang Vector/Graph/Raw là eventual consistent với `idempotency_key`. Vector/Graph/Raw có thể rebuild từ Metadata. Xem `docs/engines/knowledge-storage-engine.md#write-path`.

## Consequences

- (+) Mỗi engine dùng store tối ưu cho access pattern của nó.
- (+) Independent scaling per layer.
- (-) Phải implement outbox + reconciler + nightly consistency check.
- (-) Prod cần vận hành 3 hệ thống (Postgres, Neo4j, S3) thay vì 1.

## Alternatives Considered

- **Single Postgres + pgvector + Apache AGE (graph):** đơn giản hơn nhưng AGE kém mature so với Neo4j, và vẫn cần S3 cho raw.
- **Weaviate/Qdrant hybrid (vector+graph):** hứa hẹn nhưng chưa đủ mature cho RBAC và lifecycle filtering như Postgres.
- **Milvus:** scale tốt nhưng thêm infra phức tạp cho MVP — loại vì over-engineering.
- **Chỉ dùng SQLite + Chroma + NetworkX cho cả prod:** không scale khi >100k entities — không phù hợp prod enterprise.

## Decision Drivers

- MVP phải chạy được với `pip install` không cần Docker — nên chọn embedded dev stores.
- Prod phải ACID và có backup/replication — nên chọn Postgres/Neo4j/S3.
