# Day 22 — Graph Traversal & Reranking (Phase 5)

> **Phase:** 5 — Retrieval Intelligence Engine | **Date:** Day 22 of 45 | **Goal:** Implement graph traversal, reranking, and deduplication

---

## 🎯 Daily Target

**Deliverable:** Graph traverser, reranker, and deduplicator for refined retrieval results

---

## ✅ Tasks

### 1. GraphTraverser (`graph_traverser.py`)
- [ ] BFS/DFS traversal with configurable depth limit (default=3 hops)
- [ ] Methods:
  - `traverse(entity_id, direction="both", depth=3)`
  - `traverse_pattern(entity_ids, pattern="DEPENDS_ON,CALLS")`
  - `get_connected_component(entity_id, max_hops)`
- [ ] Relationship type filtering
- [ ] Lifecycle-aware traversal (exclude SUPERSEDED/DEPRECATED)
- [ ] Return traversed nodes with relationship paths

### 2. Reranker (`reranker.py`)
- [ ] Weighted scoring per `core/6-retrieval-strategy.md`:
  - confidence_weight: 0.3
  - lifecycle_weight: 0.2 (ACTIVE > UPDATED > others)
  - recency_weight: 0.1 (prefer recently updated)
  - relevance_weight: 0.4 (query relevance score)
- [ ] `rerank(results: list[ScoredResult]) -> list[ScoredResult]`
- [ ] Configurable weights via config
- [ ] Lifecycle-based scoring:
  - ACTIVE = 1.0, UPDATED = 0.8, EXTRACTED = 0.7
  - SUPERSEDED = 0.0, DEPRECATED = 0.0, ARCHIVED = 0.0

### 3. Deduplicator (`deduplicator.py`)
- [ ] Merge overlapping results:
  - Same KnowledgeObject from multiple strategies
  - Fuzzy content matching (threshold=0.85)
- [ ] Keep highest confidence version
- [ ] Merge source references
- [ ] Return deduplicated list with provenance info

### 4. Retrieval Pipeline Integration
- [ ] Connect HybridRetriever + GraphTraverser + Reranker + Deduplicator
- [ ] Process flow: Query → Plan → Retrieve → Traverse → Rerank → Deduplicate → Results

### 5. Unit Tests (`tests/unit/test_reranker.py`, `tests/unit/test_deduplicator.py`)
- [ ] Test graph traversal with various depths
- [ ] Test Reranker weighted scoring
- [ ] Test Deduplicator merging
- [ ] Test lifecycle filtering in traversal
- [ ] End-to-end retrieval pipeline

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Graph traversal with configurable depth | ☐ |
| Reranker weighted scoring works correctly | ☐ |
| Deduplicator merges overlapping results | ☐ |
| Lifecycle-aware traversal | ☐ |
| Full pipeline produces ordered results | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 23 (Pipeline tests)
- **Blocked by:** Day 20 (Query planner), Day 21 (Hybrid retrieval)

---

## 📝 Notes

- BFS for shallow paths, DFS for deep paths
- Reranker should be pluggable (different strategies)
- Deduplicator logs merges for audit
- Commit: `feat: graph traverser, reranker, and deduplicator`