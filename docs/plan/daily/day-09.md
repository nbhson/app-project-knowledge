# Day 9 — Dependency & Call Graph (Phase 2)

> **Phase:** 2 — Code Intelligence Engine | **Date:** Day 9 of 30 | **Goal:** Implement DependencyAnalyzer and CallGraphBuilder for cross-file analysis

---

## 🎯 Daily Target

**Deliverable:** Dependency analyzer and call graph builder that maps module dependencies and function call relationships

---

## ✅ Tasks

### 1. DependencyAnalyzer (`dependency_analyzer.py`)
- [ ] Analyze imports → module dependencies (DEPENDS_ON relationships)
- [ ] Track cross-module, cross-package, and cross-repo dependencies
- [ ] Detect import types: regular, wildcard, selective, alias
- [ ] Support language-specific import detection (Python, TypeScript, Java, Go)
- [ ] Handle conditional imports and conditional dependencies

### 2. CallGraphBuilder (`call_graph_builder.py`)
- [ ] Build function call graph across files (CALLS relationships)
- [ ] Analyze function signatures to detect call patterns
- [ ] Track call directions (A calls B, B is called by A)
- [ ] Handle recursive calls and mutual recursion detection
- [ ] Support inter-file calls (functions in different files/modules)

### 3. Inter-file Dependency Map
- [ ] Build dependency map: module → dependent modules
- [ ] Track version constraints and compatibility
- [ ] Detect implicit dependencies (shared configs, environment variables)

### 4. Circular Dependency Detection
- [ ] Implement cycle detection algorithm (Tarjan's or DFS-based)
- [ ] Report circular dependencies with full path
- [ ] Suggest breaking strategies (interface extraction, dependency injection)

### 5. Output: KnowledgeObject Relationships
- [ ] DEPENDS_ON relationships (module→module)
- [ ] CALLS relationships (function→function)
- [ ] EXTENDS relationships (class→parent class)
- [ ] IMPLEMENTS_IFACE relationships (class→interface)

### 6. Unit Tests (`tests/unit/test_dependency_analyzer.py`, `tests/unit/test_call_graph_builder.py`)
- [ ] Test import analysis on sample Python/TS/Java projects
- [ ] Test cross-module dependency detection
- [ ] Test circular dependency detection
- [ ] Test call graph construction
- [ ] Validate output KnowledgeObject structures

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Analyzes Python imports correctly | ☐ |
| Detects cross-module dependencies | ☐ |
| Builds function call graph across files | ☐ |
| Detects circular dependencies with path | ☐ |
| Handles multiple languages (Python, TS, Java) | ☐ |
| Output has correct KnowledgeObject types | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 10 (Code enrichment), Day 11 (Integration)
- **Blocked by:** Day 8 (Parser output provides AST data)

---

## 📝 Notes

- Use tree-sitter AST traversal for import/call extraction
- Cache dependency analysis results per file to avoid re-parsing
- Store graph data in NetworkX for efficient traversal
- Commit: `feat: dependency analyzer and call graph builder with cycle detection`