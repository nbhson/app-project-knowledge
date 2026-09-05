# Day 11 — Code Engine Tests & Integration (Phase 2)

> **Phase:** 2 — Code Intelligence Engine | **Date:** Day 11 of 30 | **Goal:** Test parser accuracy, validate call graphs, benchmark performance, integrate with ingestion

---

## 🎯 Daily Target

**Deliverable:** Comprehensive tests for code intelligence engine with benchmarks and integration with ingestion pipeline

---

## ✅ Tasks

### 1. Parser Tests
- [ ] Test parser on sample Python/TypeScript/Java projects
- [ ] Validate class hierarchy detection
- [ ] Validate function/method extraction
- [ ] Test import analysis
- [ ] Test error recovery on malformed code

### 2. Call Graph Validation
- [ ] Validate call graph accuracy against known patterns
- [ ] Test cross-file call detection
- [ ] Test cycle detection
- [ ] Verify graph structure with visualization

### 3. Cross-linking Tests
- [ ] Test JIRA reference detection
- [ ] Test Confluence docstring link detection
- [ ] Verify Requirement → Code traceability

### 4. Performance Benchmarks
- [ ] Benchmark: parsing speed for 10k+ line projects (< 1 min for typical project)
- [ ] Memory usage benchmarks
- [ ] Incremental parsing performance (re-parse only changed files)
- [ ] Cache effectiveness metrics

### 5. Integration with Ingestion Engine
- [ ] Wire code parser into ingestion pipeline
- [ ] Auto-trigger parser on new/modified code files
- [ ] Store parser results in storage engine
- [ ] Update knowledge graph with new entities/relationships

### 6. Integration Tests (`tests/integration/test_code_intelligence.py`)
- [ ] End-to-end: ingest repo → parse code → generate embeddings
- [ ] Verify ChromaDB storage of code knowledge
- [ ] Verify graph storage of call relationships
- [ ] Test with real Python/TypeScript/Java projects

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Parser handles 10k+ line projects in <1 min | ☐ |
| Call graph detection accuracy >90% on test cases | ☐ |
| Cycle detection works for circular dependencies | ☐ |
| Cross-link detection works (JIRA/Confluence) | ☐ |
| Code parser integrated with ingestion pipeline | ☐ |
| Integration tests pass with real projects | ☐ |
| Performance benchmarks documented | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Phase 3 (Extraction engine)
- **Blocked by:** Day 8-10 (Parser, Analyzer, Enricher)

---

## 📝 Notes

- Use pytest fixtures with sample code files
- Use `pytest-benchmark` for performance testing
- Add timing decorators to parser methods
- Document performance characteristics in code comments
- Commit: `feat: code intelligence tests, benchmarks, and ingestion integration`