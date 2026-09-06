# Day 20 — Intent Detection & Query Planning (Phase 5)

> **Phase:** 5 — Retrieval Intelligence Engine | **Date:** Day 20 of 45 | **Goal:** Implement intent classifier and query planner for intelligent retrieval

---

## 🎯 Daily Target

**Deliverable:** Intent classifier with 8 intent types and query planner for complex queries

---

## ✅ Tasks

### 1. IntentClassifier
- [ ] Classify queries into 8 intent types:
  - **CODE_UNDERSTANDING**: "How does PaymentService work?"
  - **REQUIREMENT_TRACEABILITY**: "Which stories implement auth?"
  - **ARCHITECTURE**: "Why did we choose Kafka?"
  - **IMPACT_ANALYSIS**: "What breaks if I change the payment DB?"
  - **BUG_INVESTIGATION**: "Why is checkout failing?"
  - **API_USAGE**: "How do I call the payment API?"
  - **COMPARISON**: "Compare Stripe vs PayPal"
  - **SUMMARY**: "Summarize the payment module"
- [ ] Implementation:
  - Keyword patterns + LLM classifier (fallback)
  - Confidence scoring per intent
  - Configurable thresholds

### 2. QueryPlanner
- [ ] Decompose complex queries:
  - Multi-part: "What depends on X and what does X depend on?"
  - Temporal: "What changed in the auth module last week?"
  - Comparative: "Compare A vs B"
- [ ] Strategy selection matrix (from `core/6-retrieval-strategy.md`):
  - CODE_UNDERSTANDING → Vector + Graph
  - REQUIREMENT_TRACEABILITY → Graph + Keyword
  - ARCHITECTURE → Vector + Graph traversal (DECISION nodes)
  - IMPACT_ANALYSIS → Graph (incoming edges) + Vector
  - BUG_INVESTIGATION → Vector + Keyword (error patterns)
  - API_USAGE → Vector (API_SPEC, ENDPOINT) + Keyword
  - COMPARISON → Vector (both entities) + Graph (relationships)
  - SUMMARY → Vector + Keyword (high recall)
- [ ] Output: `QueryPlan` with strategies, filters, parameters

### 3. QueryPlan Data Structure
- [ ] Fields:
  - `intent: IntentType`
  - `strategies: list[SearchStrategy]` (vector, keyword, graph)
  - `filters: dict` (entity_type, lifecycle_state, source_type)
  - `entity_ids: list[str]` (for graph traversal)
  - `temporal_filter: str | None` (ISO date string)
  - `max_depth: int` (for graph traversal, default=3)
  - `top_k: int` (default=20)

### 4. Unit Tests (`tests/unit/test_query_planner.py`)
- [ ] Test intent classification on sample queries
- [ ] Test query plan generation per intent
- [ ] Test strategy selection matrix
- [ ] Test temporal query handling
- [ ] Test comparative query handling

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Classifies all 8 intent types correctly | ☐ |
| Query plan selects correct strategies per intent | ☐ |
| Handles multi-part queries correctly | ☐ |
| Handles temporal queries correctly | ☐ |
| Handles comparative queries correctly | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 21 (Hybrid retrieval), Day 27 (CLI query)
- **Blocked by:** Day 19 (Storage integration for retrieval)

---

## 📝 Notes

- Use template patterns + LLM for intent classification
- Log all classifications for audit/improvement
- Confidence threshold: < 0.5 → default strategy
- Commit: `feat: intent classifier and query planner with strategy matrix`