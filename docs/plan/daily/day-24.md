# Day 24 — Context Assembly (Phase 6)

> **Phase:** 6 — Context Delivery Engine | **Date:** Day 24 of 45 | **Goal:** Implement ContextPackage, assembler, and smart compression

---

## 🎯 Daily Target

**Deliverable:** Context assembler with 5-tier compression for model-ready context packages

---

## ✅ Tasks

### 1. Define ContextPackage (`assembler.py`)
- [ ] Pydantic model (from `core/7-context-contract.md`):
  - `query: str`
  - `knowledge: list[KnowledgeChunk]`
  - `relationships: list[RelationshipChunk]`
  - `confidence: float`
  - `sources: list[SourceReference]`
  - `lifecycle_states: dict[str, LifecycleState]`
  - `warnings: list[str]`
  - `intent: IntentType`
  - `search_stats: SearchStats` (latency, results_count, strategies_used)

### 2. ContextAssembler
- [ ] Group retrieval results into coherent packages
- [ ] Enrich chunks with source references
- [ ] Attach relationship context (neighbors up to depth 2)
- [ ] Calculate overall confidence score
- [ ] Add intent and search statistics

### 3. ContextCompressor (5-Tier)
- [ ] **Tier 1: Confidence-based pruning** — remove chunks < confidence_threshold
- [ ] **Tier 2: Lifecycle-based pruning** — remove SUPERSEDED, DEPRECATED, ARCHIVED
- [ ] **Tier 3: Relevance-based truncation** — keep top-K most relevant
- [ ] **Tier 4: Content compression** — summarize long chunks (LLM-based)
- [ ] **Tier 5: Relationship pruning** — remove low-confidence edges
- [ ] Configurable thresholds per tier
- [ ] Token counting with `tiktoken` for accurate context window estimation

### 4. KnowledgeChunk & RelationshipChunk
- [ ] `KnowledgeChunk`: knowledge_id, title, content, entity_type, confidence, source_ref
- [ ] `RelationshipChunk`: from_id, to_id, relationship_type, confidence

### 5. Unit Tests (`tests/unit/test_assembler.py`)
- [ ] Test ContextPackage creation
- [ ] Test assembler with retrieval results
- [ ] Test all 5 compression tiers
- [ ] Test token counting accuracy
- [ ] Test edge cases (empty results, large contexts)

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| ContextPackage model matches spec | ☐ |
| Assembler groups and enriches results | ☐ |
| All 5 compression tiers implemented | ☐ |
| Token counting works with tiktoken | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 25 (Model adapters), Day 26 (Contract/streaming)
- **Blocked by:** Day 23 (Retrieval pipeline)

---

## 📝 Notes

- Use `tiktoken` for token counting (model-specific encodings)
- Compression should be deterministic for caching
- Log compression decisions for debugging
- Commit: `feat: context assembler with 5-tier compression and token counting`