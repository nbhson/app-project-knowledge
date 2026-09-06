# Knowledge Design Layer

> Answers: What is knowledge?

---

## What This Layer Defines

This layer defines the semantic foundation that EVERY engine in the system must respect. It answers: what can exist? How do things connect? How does knowledge evolve? Where does it come from?

---

## Key Artifacts

### 1. Entity Taxonomy

The complete list of entity types that can exist in the system:

**Code Entities:** REPOSITORY, MODULE, PACKAGE, FILE, CLASS, INTERFACE, FUNCTION, METHOD, ENUM, TYPE, VARIABLE

**Project Entities:** EPIC, STORY, TASK, BUG

**Document Entities:** DOCUMENT, REQUIREMENT, DECISION, BUSINESS_RULE

**System Entities:** API, DATABASE, SERVICE, ENDPOINT

> **Note:** Legacy aliases `ADR→DECISION`, `API_SPEC→API`, `COMPONENT/INFRASTRUCTURE→SERVICE` are mapped via `EntityType._missing_` for DB compat and not counted in the 23 canonical types.

Each entity type has a defined set of properties (see `core/3-knowledge-model.md`).

### 2. Relationship Taxonomy

The complete list of relationship types:

IMPLEMENTS, DEPENDS_ON, CALLS, USES, OWNS, DOCUMENTS, REQUIRES, SUPERSEDES, RELATED_TO, AFFECTS, PART_OF, TRACES_TO, CONTAINS, EXTENDS, IMPLEMENTS_IFACE

### 3. Source Reference Model

How every knowledge object traces back to its origin:

```python
class SourceReference(BaseModel):
    source_type: SourceType          # GIT | CONFLUENCE | JIRA | DOCUMENT | API_SPEC
    source_id: str                   # commit hash, page ID, issue key
    url: str                       # direct link to source
    title: str                     # title of source
    last_synced: datetime          # when last synced
    extra: dict[str, Any]          # additional metadata
```

### 4. Lifecycle State Machine

All possible states and valid transitions:

```
DISCOVERED -> EXTRACTED -> VALIDATING -> ACTIVE
                                  -> UPDATED -> VALIDATING -> ACTIVE
ACTIVE -> SUPERSEDED -> DEPRECATED -> ARCHIVED
ACTIVE -> DEPRECATED -> ARCHIVED
```

### 5. KnowledgeObject Model

The fundamental data structure:

```python
class KnowledgeObject(BaseModel):
    id: str
    object_type: ObjectType
    title: str
    description: str
    content: str
    source_references: list[SourceReference]  # ALWAYS non-empty
    confidence: float                        # 0.0 - 1.0
    lifecycle_state: LifecycleState
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    properties: dict[str, Any]
```

---

## Relationships Between Artifacts

```
Entity Taxonomy + Relationship Taxonomy
        |                    |
        v                    v
   KnowledgeObject -----> SourceReference
        |
        v
   Lifecycle State Machine
        |
        v
   Storage Schema (Vector + Graph + Metadata + Raw)
```

---

## Rules for Engine Developers

Every engine that produces or consumes KnowledgeObjects MUST:

1. **Validate** against the Entity Taxonomy (no unknown types)
2. **Include** at least one SourceReference (no orphaned knowledge)
3. **Set** a valid LifecycleState (no invalid states)
4. **Score** confidence between 0.0 and 1.0 (no missing scores)
5. **Respect** lifecycle transitions (no jumping from DISCOVERED to ARCHIVED)

---

## Evolution of the Model

The Knowledge Model is intentionally stable. Changes to the taxonomy require:

1. Migration script for existing data
2. Backward-compatible serialization
3. Version tracking in the KnowledgeObject schema
4. Documentation update

This ensures that adding a new entity type (e.g., `CONTAINER` for Docker) doesn't break existing queries.