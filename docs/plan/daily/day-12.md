# Day 12 — Entity & Relationship Extraction (Phase 3)

> **Phase:** 3 — Knowledge Extraction Engine | **Date:** Day 12 of 30 | **Goal:** Implement rule-based entity and relationship extraction from ingested data

---

## 🎯 Daily Target

**Deliverable:** Rule-based extractor for code, documents, and requirements with confidence scoring

---

## ✅ Tasks

### 1. EntityExtractor (`entity_extractor.py`)
- [ ] Rule-based entity identification:
  - **Code entities:** classes, functions, imports (from AST)
  - **Document entities:** headings, lists, tables
  - **Requirement entities:** epics, stories, tasks (from Jira structure)
- [ ] Extract entities from:
  - Parsed code (using tree-sitter AST)
  - Markdown documents (headings, code blocks, references)
  - Jira issues (structured data)
- [ ] Return KnowledgeObjects for each entity

### 2. RelationshipExtractor (`relationship_extractor.py`)
- [ ] Rule-based relationship mappings:
  - `import` / `from X import` → DEPENDS_ON
  - `class X extends Y` → EXTENDS
  - `class X implements Y` → IMPLEMENTS_IFACE
  - `JIRA-123` reference → TRACES_TO
  - `ADR-001` reference → DOCUMENTS
  - Function calls → CALLS
  - Parent class → EXTENDS
- [ ] Cross-source relationships:
  - Code → Jira (TRACES_TO)
  - Code → Confluence (DOCUMENTS)
  - Requirements → Docs (REQUIREMENT → DOCUMENTS)
- [ ] Extract relationships from text patterns:
  - Regex for `[ref]`, `(ref)`, cross-references
  - Markdown link analysis

### 3. Confidence Scoring
- [ ] Assign confidence per extraction method:
  - **High (1.0):** structural (code AST, Jira structured data)
  - **Medium (0.7-0.9):** inferred (text patterns, regex)
  - **Low (0.3-0.6):** LLM-based (from Day 13)
- [ ] Score based on:
  - Source reliability
  - Pattern specificity
  - Cross-validation (multiple sources agree)

### 4. Output Structures
- [ ] `ExtractedEntity`: KnowledgeObject + source info
- [ ] `ExtractedRelationship`: from_entity, to_entity, type, confidence
- [ ] `ExtractionResult`: entities, relationships, confidence map

### 5. Unit Tests (`tests/unit/test_entity_extractor.py`)
- [ ] Test code entity extraction (classes, functions, imports)
- [ ] Test document entity extraction (headings, lists)
- [ ] Test requirement entity extraction
- [ ] Test relationship extraction (extends, implements, calls, depends_on)
- [ ] Test cross-source relationships
- [ ] Validate confidence scoring logic

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Extracts code entities from AST correctly | ☐ |
| Extracts document entities from markdown | ☐ |
| Detects all 15 relationship types | ☐ |
| Cross-source relationships work | ☐ |
| Confidence scoring matches specification | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 14 (LLM extraction), Phase 4 (Storage)
- **Blocked by:** Day 3-7 (Connectors, parser)

---

## 📝 Notes

- Use regex patterns + AST traversal for rule-based extraction
- Maintain pattern registry for easy extension
- Log all extraction rules fired (audit trail)
- Commit: `feat: rule-based entity and relationship extractor with confidence scoring`