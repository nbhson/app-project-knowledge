# Knowledge Model -- Semantic Foundation

> The Knowledge Model is the semantic foundation of the entire Harness. It determines the system''s ability to understand the project.
> [[glossary]]

---

## What is Knowledge?

Knowledge is structured, traceable, and contextualized information about the project. It is distinct from raw data:

| Aspect | Raw Data | Knowledge |
|--------|----------|-----------|
| Form | Unstructured text, API responses | Structured entities + relationships |
| Meaning | Needs interpretation | Self-describing via schema |
| Traceability | May have source URL | Explicit SourceReference chain |
| Lifecycle | Static | Stateful (DISCOVERED -> ACTIVE -> ...) |
| Confidence | N/A | Scored (0.0 - 1.0) |

---

## Knowledge Object Model

Every piece of knowledge in the system is a `KnowledgeObject`:

```python
class KnowledgeObject(BaseModel):
    """The fundamental unit of knowledge in the system."""
    
    # Identity
    id: str                              # UUID v4, globally unique
    object_type: ObjectType              # ENTITY | RELATIONSHIP | DECISION | RULE
    
    # Content
    title: str                           # Human-readable name
    description: str = ""                # Free-text description
    content: str = ""                    # Full text content (for vector indexing)
    
    # Source of Truth
    source_references: list[SourceReference]  # ALWAYS non-empty
    
    # Confidence
    confidence: float = 1.0              # 0.0 - 1.0, set by extraction engine
    
    # Lifecycle
    lifecycle_state: LifecycleState = LifecycleState.DISCOVERED
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    tags: list[str] = []                 # For classification and filtering
    properties: dict[str, Any] = {}      # Type-specific extra fields
```

---

## Entity Types Taxonomy

### Code Entities

| Type | Description | Example | Key Properties |
|------|-------------|---------|----------------|
| `REPOSITORY` | A Git repository | `project-knowledge-harness` | `url`, `default_branch`, `language` |
| `MODULE` | Logical grouping of code | `payment-service` | `parent_module`, `owner_team` |
| `PACKAGE` | Language-specific namespace | `com.example.payments` | `language`, `import_path` |
| `FILE` | A source code file | `PaymentService.java` | `path`, `language`, `size_bytes` |
| `CLASS` | An OOP class definition | `PaymentService` | `extends`, `implements`, `file_path` |
| `INTERFACE` | An interface/type definition | `PaymentGateway` | `methods`, `file_path` |
| `FUNCTION` | A standalone function | `processPayment()` | `signature`, `file_path`, `line_start`, `line_end` |
| `METHOD` | A class method | `PaymentService.charge()` | `class_name`, `signature`, `file_path` |
| `ENUM` | An enumeration type | `PaymentStatus` | `values`, `file_path` |
| `TYPE` | A type alias or struct | `PaymentRequest` | `fields`, `file_path` |
| `VARIABLE` | A variable declaration | `MAX_RETRIES` | `type`, `value`, `scope` |

### Project Entities

| Type | Description | Example | Key Properties |
|------|-------------|---------|----------------|
| `EPIC` | A large body of work | `Payment Platform Redesign` | `parent_epic`, `status`, `story_count` |
| `STORY` | A user-facing requirement | `As a user, I want to pay via credit card` | `acceptance_criteria`, `epic_key` |
| `TASK` | A unit of work | `Implement Stripe integration` | `story_key`, `assignee`, `estimate` |
| `BUG` | A defect | `Payment fails on timeout` | `severity`, `reported_by`, `sprint` |

### Document Entities

| Type | Description | Example | Key Properties |
|------|-------------|---------|----------------|
| `DOCUMENT` | A Confluence page or doc file | `Architecture Overview` | `format`, `last_edited_by`, `space` |
| `REQUIREMENT` | A specific requirement | `System must handle 1000 TPS` | `source_doc`, `priority`, `type` |
| `DECISION` | An architecture/design decision (ADR) | `ADR-001: Use Kafka for async` | `status`, `decision_type`, `consequences` |
| `BUSINESS_RULE` | A business constraint or rule | `Payments under $10 skip verification` | `rule_type`, `applicable_to`, `enforced_by` |

### System Entities

| Type | Description | Example | Key Properties |
|------|-------------|---------|----------------|
| `API` | An API endpoint or service | `POST /api/payments` | `method`, `path`, `request_schema`, `response_schema` |
| `DATABASE` | A database or table | `payments_db` | `type`, `host`, `tables` |
| `SERVICE` | A running service | `payment-service` | `host`, `port`, `dependencies`, `health_check` |
| `ENDPOINT` | A specific API endpoint | `/api/payments/charge` | `method`, `auth_required`, `rate_limit` |

---

## Relationship Types Taxonomy

| Relationship | Direction | Meaning | Example |
|-------------|-----------|---------|---------|
| `IMPLEMENTS` | Knowledge -> Project | Code implements a requirement | `PaymentService IMPLEMENTS STORY-123` |
| `DEPENDS_ON` | Code -> Code | Module depends on another | `AuthModule DEPENDS_ON CryptoLib` |
| `CALLS` | Function -> Function | Function calls another | `processPayment() CALLS validateCard()` |
| `USES` | Component -> Component | Component uses another | `Frontend USES PaymentAPI` |
| `OWNS` | Team -> Code | Ownership relationship | `Team-A OWNS PaymentService` |
| `DOCUMENTS` | Doc -> Entity | Doc describes something | `ADR-001 DOCUMENTS KafkaDecision` |
| `REQUIRES` | Story -> Entity | Requirement needs something | `STORY-456 REQUIRES API-789` |
| `SUPERSEDES` | Decision -> Decision | New replaces old | `ADR-002 SUPERSEDES ADR-001` |
| `RELATED_TO` | Entity -> Entity | General connection | `AuthModule RELATED_TO LoggingModule` |
| `AFFECTS` | Change -> Impact | Impact relationship | `DBSchemaChange AFFECTS QueryPerf` |
| `PART_OF` | Child -> Parent | Compositional | `PaymentService PART_OF CheckoutModule` |
| `TRACES_TO` | Knowledge -> Source | Source provenance | `KnowledgeObj TRACES_TO GitCommit` |
| `CONTAINS` | Parent -> Child | Structural containment | `Module CONTAINS File` |
| `EXTENDS` | Class -> Class | Inheritance | `SubClass EXTENDS SuperClass` |
| `IMPLEMENTS_IFACE` | Class -> Interface | Interface implementation | `PaymentService IMPLEMENTS_IFACE IPayment` |

---

## SourceReference Model

Every KnowledgeObject carries one or more SourceReferences:

```python
class SourceReference(BaseModel):
    """Traceability link back to the original source."""
    
    source_type: SourceType              # GIT | CONFLUENCE | JIRA | DOCUMENT | API_SPEC
    source_id: str                       # commit hash, page ID, issue key, etc.
    url: str = ""                        # direct link to source
    title: str = ""                      # title of source
    last_synced: datetime                # when last synced
    extra: dict[str, Any] = {}           # additional metadata (e.g., line numbers, field names)
```

**Source type specifics:**

| SourceType | source_id format | url format | extra keys |
|------------|------------------|------------|------------|
| `GIT` | commit hash (40 chars) | `https://github.com/.../commit/<hash>` | `branch`, `file_path`, `line_start`, `line_end` |
| `CONFLUENCE` | page ID (numeric) | `https://org.atlassian.net/wiki/page/<id>` | `space_key`, `version`, `content_type` |
| `JIRA` | issue key (e.g., `PROJ-123`) | `https://org.atlassian.net/browse/<key>` | `issue_type`, `field_name` |
| `DOCUMENT` | file path (relative to repo root) | N/A | `format`, `encoding`, `size_bytes` |
| `API_SPEC` | spec file path + endpoint path | N/A | `method`, `path`, `spec_version` |

---

## How the Model Works

The Knowledge Model defines four things that every engine must respect:

1. **What can exist** - The Entity Type taxonomy (all possible kinds of things)
2. **How things connect** - The Relationship Type taxonomy (all possible connections)
3. **Where knowledge comes from** - The SourceReference model (traceability)
4. **How knowledge evolves** - The Lifecycle state machine (valid transitions)

Every KnowledgeObject MUST conform to this model. Engines that produce KnowledgeObjects validate against it. Engines that consume KnowledgeObjects rely on it for structure.