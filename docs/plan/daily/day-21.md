# Day 21 — Hybrid Retrieval (Phase 5)

> **Phase:** 5 — Retrieval Intelligence Engine | **Date:** Day 21 of 30 | **Goal:** Implement parallel hybrid retrieval with vector, keyword, and graph strategies

---

## 🎯 Daily Target

**Deliverable:** Hybrid retriever with parallel execution and Reciprocal Rank Fusion (RRF) scoring

---

## ✅ Tasks

### 1. HybridRetriever Implementation
- [ ] Parallel execution of 3 strategies:
  - **Vector search**: semantic similarity via embeddings
  - **Keyword search**: full-text inverted index (BM25 or similar)
  - **Graph traversal**: relationship-based discovery
- [ ] Use `asyncio.gather` for parallel execution
- [ ] Each strategy has timeout (200ms) and returns partial results
- [ ] Handle partial failures gracefully (one strategy fails, others continue)

### 2. Reciprocal Rank Fusion (RRF)
- [ ] Implement RRF formula:
  ```
  score(result) = sum(1 / (k + rank_in_strategy) for strategy in strategies)
  ```
  where k = 60 (default)
- [ ] Configurable k value per query type
- [ ] Handle ties (same score → use confidence as tiebreaker)

### 3. Configurable Weights
- [ ] Weights per intent type (from config):
  - CODE_UNDERSTANDING: Vector 0.5, Keyword 0.2, Graph 0.3
  - REQUIREMENT_TRACEABILITY: Vector 0.2, Keyword 0.3, Graph 0.5
  - etc.
- [ ] Configurable via `retrieval.config.yaml`

### 4. Keyword Search Implementation
- [ ] Implement simple inverted index for keyword search
- [ ] BM25 scoring algorithm
- [ ] Filter by entity types, lifecycle states
- [ ] Return ranked results with scores

### 5. Unit Tests (`tests/unit/test_hybrid_retriever.py`)
- [ ] Test vector search
- [ ] Test keyword search
- [ ] Test graph traversal
- [ ] Test RRF fusion
- [ ] Test parallel execution with timeouts
- [ ] Test weights configuration

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Parallel execution works (all 3 strategies) | ☐ |
| RRF fusion produces correct scores | ☐ |
| Configurable weights per intent | ☐ |
| Timeout handling works | ☐ |
| Keyword search returns relevant results | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 22 (Reranking), Day 23 (Pipeline)
- **Blocked by:** Day 20 (Query planner), Day 19 (Storage)

---

## 📝 Notes

- Use `asyncio` for parallel strategy execution
- Implement circuit breaker pattern for failing strategies
- Log strategy execution times for monitoring
- Commit: `feat: hybrid retriever with parallel execution and rrf fusion`