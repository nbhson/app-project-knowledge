# Day 10 — Code Knowledge Enrichment (Phase 2)

> **Phase:** 2 — Code Intelligence Engine | **Date:** Day 10 of 45 | **Goal:** Map code to requirements/docs, generate embeddings, cross-link entities

---

## 🎯 Daily Target

**Deliverable:** Cross-linking code to Jira requirements and Confluence docs with semantic embeddings

---

## ✅ Tasks

### 1. Map Code → Jira Requirements
- [ ] Detect `JIRA-123` references in comments and docstrings
- [ ] Detect `#123` references in comments
- [ ] Map code entities (class/function) to associated Jira issues
- [ ] Create TRACES_TO relationships (Code → Requirement)

### 2. Map Code → Confluence Docs
- [ ] Detect docstring links to Confluence pages
- [ ] Detect README.md references
- [ ] Detect `@see`, `@link` annotations
- [ ] Create DOCUMENTS relationships (Code → Document)

### 3. Tag Code with Architectural Context
- [ ] Module boundaries detection (package structure)
- [ ] Package/directory structure → architecture layers
- [ ] Tag code with domain context (e.g., `domain/payment`, `domain/order`)

### 4. Generate Embeddings
- [ ] Semantic description of each code entity
- [ ] Embedding model: text-embedding-3-small (OpenAI)
- [ ] Embed code snippets, docstrings, comments
- [ ] Store embeddings in ChromaDB

### 5. Cross-link: Code ↔ Requirement ↔ Document
- [ ] Bi-directional relationships:
  - Code → Requirement (TRACES_TO)
  - Requirement → Code (IMPLEMENTS)
  - Code → Document (DOCUMENTS)
  - Document → Code (DESCRIBES)
- [ ] Full traceability graph from requirement to implementation

### 6. Unit Tests
- [ ] Test JIRA reference detection in code comments
- [ ] Test Confluence docstring link detection
- [ ] Test architectural tagging
- [ ] Test embedding generation and storage
- [ ] Validate cross-link relationships

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Detects JIRA references in code | ☐ |
| Detects Confluence links in docstrings | ☐ |
| Tags code with domain/architectural context | ☐ |
| Generates embeddings for code entities | ☐ |
| Stores embeddings in ChromaDB | ☐ |
| Cross-link relationships verified | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 11 (Integration tests), Phase 3 (Extraction needs enrichment)
- **Blocked by:** Day 8-9 (Parser, DependencyAnalyzer, CallGraphBuilder)

---

## 📝 Notes

- Use regex patterns for JIRA-XXX, #XXX detection
- Use `tree-sitter` for comment/docstring extraction
- Embeddings should be generated in batches for efficiency
- Commit: `feat: code enrichment with Jira/Confluence mapping, embeddings, cross-linking`