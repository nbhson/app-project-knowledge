# Day 15 — Extraction Pipeline & Validation (Phase 3)

> **Phase:** 3 — Knowledge Extraction Engine | **Date:** Day 15 of 45 | **Goal:** Complete 3-pass pipeline, knowledge validator, conflict resolution

---

## 🎯 Daily Target

**Deliverable:** Working 3-pass extraction pipeline with validation and auto-supersede

---

## ✅ Tasks

### 1. Build 3-Pass Pipeline (`pipeline.py`)
- [ ] **Pass 1: Rule-based extraction**
  - EntityExtractor (from Day 12)
  - RelationshipExtractor (from Day 12)
  - Confidence scoring (high for structural)
- [ ] **Pass 2: LLM enrichment**
  - LLMExtractionAdapter (from Day 13)
  - Enrich entities with descriptions, relationships
  - Detect missing relationships
  - Confidence: medium for inferred
- [ ] **Pass 3: Confidence scoring & merging**
  - Combine scores from both passes
  - Weighted average with source preference
  - Remove duplicates (merge same entity from multiple sources)
- [ ] Output: merged KnowledgeObject list with final confidence

### 2. Implement KnowledgeValidator (`knowledge_validator.py`)
- [ ] Quality gates from `domains/knowledge-acquisition.md`:
  - **Source reference present** (required): every KnowledgeObject must have ≥1 SourceReference
  - **Content non-empty**: title and content must not be empty
  - **Confidence assigned** (0.0-1.0): validate range
  - **Lifecycle state valid**: must be valid LifecycleState enum value
- [ ] Orphan detection: entities without relationships flagged
- [ ] Duplicate detection: similar KnowledgeObjects flagged for merge
- [ ] Staleness check: entities older than threshold flagged

### 3. Auto-Supersede Logic
- [ ] New conflicting knowledge → mark old as SUPERSEDED
- [ ] Conflict resolution rules:
  - Higher confidence wins
  - More recent wins (if equal confidence)
  - Source trustworthiness tiebreaker
- [ ] Record supersede reason in lifecycle_events
- [ ] Preserve old version (not delete) for audit

### 4. Conflict Resolution
- [ ] Per `core/5-source-of-truth-model.md`:
  - Source hierarchy defines which source wins
  - Git source > Confluence > Jira > Documents
  - Structured data > text data
  - Multiple sources > single source
- [ ] Manual override option (admin only)

### 5. Write Validation Tests (`tests/unit/test_pipeline.py`)
- [ ] Test 3-pass pipeline end-to-end
- [ ] Test confidence scoring merge logic
- [ ] Test orphan detection
- [ ] Test duplicate detection and merge
- [ ] Test staleness detection
- [ ] Test auto-supersede logic
- [ ] Test conflict resolution per source hierarchy

### 6. Integration with Storage
- [ ] Pipeline output feeds into Storage Engine
- [ ] Store validated KnowledgeObjects
- [ ] Update relationships in graph store

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| 3-pass pipeline runs correctly | ☐ |
| All quality gates pass (source ref, content, confidence, lifecycle) | ☐ |
| Orphan detection works | ☐ |
| Duplicate detection works | ☐ |
| Auto-supersede marks old as SUPERSEDED | ☐ |
| Conflict resolution follows source hierarchy | ☐ |
| Unit tests pass | ☐ |
| Pipeline integrates with storage engine | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 16-19 (Storage engine consumes validated knowledge)
- **Blocked by:** Day 12-14 (All extraction components)

---

## 📝 Notes

- Pipeline should be modular — each pass swappable
- Use `asyncio` for parallel LLM enrichment
- Validate before storing — never store invalid knowledge
- Commit: `feat: 3-pass extraction pipeline, validator, conflict resolution`