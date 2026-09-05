# Engine 2: Code Intelligence Engine

> Execution Capability: Understand code structurally at the AST level.
> [[glossary]]

---

## Role

Parse source code into structured representations -- not just text, but meaningful code entities and relationships. This engine transforms raw code files into a navigable graph of code entities.

---

## Architecture

```
Raw Code Files (from Engine 1)
         |
         v
+----------------------+
|  CodeParser          |  Language-agnostic AST parser (tree-sitter)
|  (per-language)      |  Python, TypeScript, Java, Go, Rust, etc.
+----------------------+
         |
         v
+----------------------+
|  SymbolTableBuilder  |  Build symbol registry: classes, functions, variables
|                      |  Resolve references across files
+----------------------+
         |
         v
+----------------------+
|  DependencyAnalyzer  |  Find import/require/depends relationships
|                      |  Build module/package hierarchy
+----------------------+
         |
         v
+----------------------+
|  CallGraphBuilder    |  Track function/method call relationships
|                      |  Distinguish direct calls from indirect
+----------------------+
         |
         v
CodeKnowledgeOutput -> feeds into Engine 3 (Extraction)
```

---

## Language Support — Incremental (Anti Complexity)

> **Rủi ro:** Mỗi parser có AST khác nhau, mapping về `EntityType` phức tạp, làm chậm MVP.

| Phase | Languages | Parser | AST Nodes | Gate |
|-------|-----------|--------|-----------|------|
| **MVP (Day 8)** | **Python only** | `tree-sitter-python` | Class, Function, Method, Import, Decorator | `pytest tests/unit/test_code_parser_python.py` pass trên 1 repo Python sample |
| **Phase 2 (Day 11+)** | + TypeScript/JavaScript | `tree-sitter-typescript` | + Interface, TypeAlias | Thêm sau khi Python ổn |
| **Phase 3 (Later)** | + Java, Go, Rust, C/C++ | respective `tree-sitter-*` | Struct, etc. | Mỗi ngôn ngữ là plugin riêng, thêm khi có nhu cầu thực tế — không block MVP |

**Quy tắc:**
- `CodeParser` là interface chung (`parse(file_path) -> list[CodeEntity]`). Mỗi ngôn ngữ là adapter riêng trong `src/pkh/engines/code_intelligence/parsers/`.
- Nếu parser fail (syntax error), fallback về **text-based extraction** (regex class/function) và ghi `confidence=0.5, warnings` — không fail cả file.
- Không hỗ trợ ngôn ngữ mới cho đến khi `benchmark: <1min cho 10k lines Python` đạt.

## Supported Languages (Full Scope — Post-MVP)

| Language | Parser | AST Nodes Extracted | Notes |
|----------|--------|---------------------|-------|
| Python | `tree-sitter-python` | Class, Function, Method, Import, Decorator | MVP — Full support |
| TypeScript | `tree-sitter-typescript` | Class, Function, Method, Interface, TypeAlias, Import | Post-MVP |
| JavaScript | `tree-sitter-javascript` | Class, Function, Method, Import, Export | Post-MVP |
| Go | `tree-sitter-go` | Struct, Function, Method, Import | Later |
| Rust | `tree-sitter-rust` | Struct, Function, Method, Impl, Import | Later |
| Java | `tree-sitter-java` | Class, Interface, Method, Import | Later |
| C/C++ | `tree-sitter-c` / `tree-sitter-cpp` | Struct, Function, Method, Include | Later — Basic support |

---

## CodeEntity Model

```python
class CodeEntity(BaseModel):
    """A code entity extracted from source files."""
    
    id: str                              # UUID
    kind: CodeEntityKind                 # REPOSITORY | MODULE | PACKAGE | FILE | CLASS | FUNCTION | METHOD | INTERFACE | ENUM | TYPE | VARIABLE
    name: str
    file_path: str                       # Relative to repository root
    line_start: int
    line_end: int
    signature: str = ""                  # e.g., "processPayment(amount: float) -> bool"
    documentation: str = ""              # Docstring / comment
    parents: list[str] = []              # Parent entity IDs
    children: list[str] = []             # Child entity IDs
    relationships: list[CodeRelationship] = []
    metadata: dict[str, Any] = {}        # Language-specific extra info
    
    # Source reference (inherited from KnowledgeObject)
    source_references: list[SourceReference]
```

```python
class CodeRelationship(BaseModel):
    from_entity: str
    to_entity: str
    type: CodeRelationshipType           # DEPENDS_ON | CALLS | EXTENDS | IMPLEMENTS_IFACE | CONTAINS
    confidence: float = 1.0
```

```python
class CodeEntityKind(str, Enum):
    REPOSITORY = "repository"
    MODULE = "module"
    PACKAGE = "package"
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface"
    FUNCTION = "function"
    METHOD = "method"
    ENUM = "enum"
    TYPE = "type"
    VARIABLE = "variable"

class CodeRelationshipType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS_IFACE = "IMPLEMENTS_IFACE"
    CONTAINS = "CONTAINS"
```

---

## Output

Code entities are output as KnowledgeObjects with `object_type = ENTITY` and entity-specific properties:

```python
# Output of Code Intelligence Engine
class CodeKnowledgeOutput(BaseModel):
    entities: list[CodeEntity]
    relationships: list[CodeRelationship]
    symbol_table: dict[str, list[str]]   # file_path -> [symbol_names]
    module_hierarchy: dict[str, list[str]]  # module -> [submodules]
    stats: ParsingStats
```

```python
class ParsingStats(BaseModel):
    files_parsed: int
    entities_found: int
    relationships_found: int
    errors: list[str]
    duration_seconds: float
```

---

## Key Design Decisions

1. **Incremental parsing**: Only re-parse files that have changed (tracked by content hash).
2. **Language plugins**: Each language is a plugin; add new languages by adding a parser plugin.
3. **Symbol resolution**: Cross-file references are resolved by building a global symbol table.
4. **No semantic analysis**: We parse structure, not semantics. Type inference is out of scope.
5. **Memory efficiency**: Large repositories are parsed in chunks; not all files loaded at once.