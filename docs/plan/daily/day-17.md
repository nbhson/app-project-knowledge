# Day 17 — Vector Store (ChromaDB)

> **Phase:** 4 — Knowledge Storage Engine | **Date:** Day 17 of 30 | **Goal:** Implement VectorStore with ChromaDB backend and embedding generation

---

## 🎯 Daily Target

**Deliverable:** Vector store interface with ChromaDB implementation for semantic search

---

## ✅ Tasks

### 1. VectorStore Interface
- [ ] Abstract base class with methods:
  - `upsert(knowledge_chunks: list[KnowledgeChunk]) -> None`
  - `query(query_embedding, top_k, filters) -> list[ScoredChunk]`
  - `delete(ids: list[str]) -> None`
  - `exists(id: str) -> bool`

### 2. ChromaDBBackend Implementation
- [ ] Initialize ChromaDB client (persistent path)
- [ ] Create collection with configurable name
- [ ] Store knowledge chunks with:
  - Embedding vector
  - Metadata: entity_type, lifecycle_state, source_type, knowledge_id
- [ ] Implement query with filters on metadata fields

### 3. EmbeddingGenerator
- [ ] `EmbeddingGenerator` class with OpenAI adapter
- [ ] Model: text-embedding-3-small (default)
- [ ] Batch embedding for efficiency
- [ ] Token counting and truncation (512 tokens max per chunk)
- [ ] Cache embeddings to avoid recomputation

### 4. Knowledge Chunking Strategy
- [ ] Chunk by entity type:
  - Code: 512 tokens, 64 token overlap
  - Documents: 512 tokens, 64 overlap
  - Requirements: full entity per chunk
- [ ] Store chunk metadata with parent KnowledgeObject ID

### 5. Unit Tests (`tests/unit/test_vector_store.py`)
- [ ] Test upsert and query
- [ ] Test metadata filtering
- [ ] Test chunking strategy
- [ ] Test embedding generation
- [ ] Test delete operations

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| ChromaDB client initializes correctly | ☐ |
| Upsert stores embeddings with metadata | ☐ |
| Query returns scored results with filters | ☐ |
| Embedding generator works with OpenAI | ☐ |
| Chunking produces correct token counts | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 19 (Storage integration), Phase 5 (Retrieval)
- **Blocked by:** Day 16 (Metadata store)

---

## 📝 Notes

- Use `chromadb` library with `HttpClient` or `PersistentClient`
- Configure persistence path from config
- Batch size for upserts: 1000
- Commit: `feat: vector store with chromadb and embedding generation`