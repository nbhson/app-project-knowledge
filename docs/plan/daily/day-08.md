# Day 8 — AST Parser Foundation (Phase 2)

> **Phase:** 2 — Code Intelligence Engine | **Date:** Day 8 of 30 | **Goal:** Implement AST parser using tree-sitter for language-agnostic code understanding

---

## 🎯 Daily Target

**Deliverable:** Working AST parser that extracts structured code knowledge (Classes, Functions, Imports) from multiple languages

---

## ✅ Tasks

### 1. Set Up Tree-sitter Environment
- [ ] Install `tree-sitter`, `tree-sitter-python`, and language-specific parsers
- [ ] Configure `src/pkh/engines/code_intelligence/parser.py` with:
  - Language-specific parsers (Python, TypeScript, Java, Go, Rust, C/C++)
  - Base `CodeParser` class with language-agnostic interface
  - `parse(file_path: str) -> list[KnowledgeObject]`

### 2. Implement Python Parser
- [ ] Use `tree-sitter-python` to parse Python files
- [ ] Extract: Class definitions (with inheritance, interfaces), Function definitions (including decorators), Import statements (module-level, relative), Method signatures (parameters, return types)
- [ ] Build symbol table per file with: Class hierarchy, Function call hierarchy, Import dependencies
- [ ] Handle parse errors gracefully with fallback to text-based extraction

### 3. Implement TypeScript Parser
- [ ] Use `tree-sitter-typescript` for TypeScript files
- [ ] Extract: Class/interface definitions, Function/method definitions, Import/export statements, Decorators (e.g., @api, @Component), Type annotations
- [ ] Build symbol table with TypeScript-specific structures

### 4. Implement Java Parser
- [ ] Use `tree-sitter-java` for Java files
- [ ] Extract: Class/interface definitions, Method signatures, Package declarations, Annotations, Inheritance/implements relationships

### 5. Implement Multi-language Support
- [ ] Detect language from file extension or content
- [ ] Use appropriate parser for each language
- [ ] Handle mixed-language files (e.g., TypeScript with JS imports)
- [ ] Fallback to text-based extraction for unsupported languages

### 6. Output: KnowledgeObject Types
- [ ] `Class` entity (object_type=ENTITY, entity_type=CLASS)
- [ ] `Function` entity (object_type=ENTITY, entity_type=FUNCTION)
- [ ] `Import` entity (object_type=ENTITY, entity_type=IMPORT)
- [ ] `Interface` entity (object_type=ENTITY, entity_type=INTERFACE)
- [ ] Relationships: `EXTENDS`, `IMPLEMENTS`, `IMPORTS`, `CALLS`

### 7. Unit Tests
- [ ] Test Python parser on sample files
- [ ] Test TypeScript parser on sample files
- [ ] Test language detection
- [ ] Test parse error fallback

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Parses Python files extracting classes, functions, imports | ☐ |
| Parses TypeScript files extracting classes, interfaces, functions | ☐ |
| Parses Java files extracting classes, methods, packages | ☐ |
| Builds symbol table per file | ☐ |
| Language detection works from extension | ☐ |
| Fallback to text extraction on parse errors | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 9 (Dependency Analyzer)
- **Blocked by:** Day 7 (CLI integration)

---

## 📝 Notes

- Tree-sitter is incremental: parse only changed files for efficiency
- Use `tree-sitter-languages` package for bundled parsers
- Store parse tree nodes with line/column for source linking
- Commit: `feat: ast parser foundation with multi-language support`
