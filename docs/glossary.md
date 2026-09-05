# Glossary

> The single source of truth for PKH terminology. All other documentation links to this file for definitions.

---

## Knowledge Model

### KnowledgeObject
The fundamental unit of knowledge in the system. Every piece of information — code, requirements, decisions, rules — is stored as a KnowledgeObject with identity, content, source references, confidence score, and lifecycle state.

**Properties:** `id`, `object_type`, `title`, `description`, `content`, `source_references`, `confidence`, `lifecycle_state`, `created_at`, `updated_at`, `tags`, `properties`

### SourceReference
A traceability link from a KnowledgeObject back to its original source. Every KnowledgeObject MUST have at least one SourceReference.

**Properties:** `source_type`, `source_id`, `url`, `title`, `last_synced`, `extra`

### ContextPackage
The canonical, model-agnostic output format that PKH delivers to any LLM consumer. Contains ranked knowledge chunks, relationships, sources, and metadata.

**Properties:** `query`, `knowledge`, `relationships`, `confidence`, `sources`, `lifecycle_states`, `warnings`, `intent`, `search_stats`, `compression_ratio`

### KnowledgeChunk
A single piece of knowledge within a ContextPackage. Links back to its source and carries confidence/lifecycle metadata.

**Properties:** `id`, `type`, `title`, `content`, `confidence`, `lifecycle_state`, `relevance_score`, `rank`, `sources`

### RelationshipChunk
A relationship between two knowledge entities within a ContextPackage.

**Properties:** `from_id`, `to_id`, `type`, `confidence`

### SearchStats
Metrics about a retrieval operation, included in ContextPackage for transparency.

**Properties:** `vector_results`, `keyword_results`, `graph_results`, `total_before_dedup`, `total_after_dedup`, `strategies_used`, `latency_ms`

---

## Entity Types (23 total)

### Code Entities (11)

| Type | Description |
|------|-------------|
| `REPOSITORY` | A Git repository |
| `MODULE` | Logical grouping of code |
| `PACKAGE` | Language-specific namespace |
| `FILE` | A source code file |
| `CLASS` | An OOP class definition |
| `INTERFACE` | An interface/type definition |
| `FUNCTION` | A standalone function |
| `METHOD` | A class method |
| `ENUM` | An enumeration type |
| `TYPE` | A type alias or struct |
| `VARIABLE` | A variable declaration |

### Project Entities (4)

| Type | Description |
|------|-------------|
| `EPIC` | A large body of work |
| `STORY` | A user-facing requirement |
| `TASK` | A unit of work |
| `BUG` | A defect |

### Document Entities (4)

| Type | Description |
|------|-------------|
| `DOCUMENT` | A Confluence page or doc file |
| `REQUIREMENT` | A specific requirement |
| `DECISION` | An architecture/design decision (ADR) |
| `BUSINESS_RULE` | A business constraint or rule |

### System Entities (4)

| Type | Description |
|------|-------------|
| `API` | An API endpoint or service |
| `DATABASE` | A database or table |
| `SERVICE` | A running service |
| `ENDPOINT` | A specific API endpoint |

---

## Relationship Types (15 total)

| Type | Direction | Meaning |
|------|-----------|---------|
| `IMPLEMENTS` | Knowledge → Project | Code implements a requirement |
| `DEPENDS_ON` | Code → Code | Module depends on another |
| `CALLS` | Function → Function | Function calls another |
| `USES` | Component → Component | Component uses another |
| `OWNS` | Team → Code | Ownership relationship |
| `DOCUMENTS` | Doc → Entity | Doc describes something |
| `REQUIRES` | Story → Entity | Requirement needs something |
| `SUPERSEDES` | Decision → Decision | New replaces old |
| `RELATED_TO` | Entity → Entity | General connection |
| `AFFECTS` | Change → Impact | Impact relationship |
| `PART_OF` | Child → Parent | Compositional |
| `TRACES_TO` | Knowledge → Source | Source provenance |
| `CONTAINS` | Parent → Child | Structural containment |
| `EXTENDS` | Class → Class | Inheritance |
| `IMPLEMENTS_IFACE` | Class → Interface | Interface implementation |

---

## Lifecycle States (8 total)

| State | Description | Queryable |
|-------|-------------|-----------|
| `DISCOVERED` | Raw data found, not yet processed | No |
| `EXTRACTED` | Knowledge extracted but not yet validated | Yes (flagged) |
| `VALIDATING` | Under validation checks | No |
| `ACTIVE` | Validated and live | Yes |
| `UPDATED` | Source changed, re-validation pending | Yes (flagged) |
| `SUPERSEDED` | Replaced by newer knowledge | No |
| `DEPRECATED` | No longer in use | No |
| `ARCHIVED` | Preserved for history (read-only) | No (read-only) |

---

## Source Types (5 total)

| Type | source_id format | url format |
|------|------------------|------------|
| `GIT` | commit hash (40 chars) | GitHub commit URL |
| `CONFLUENCE` | page ID (numeric) | Confluence page URL |
| `JIRA` | issue key (e.g., PROJ-123) | Jira browse URL |
| `DOCUMENT` | file path (relative) | N/A (local reference) |
| `API_SPEC` | spec file path + endpoint | N/A |

---

## Engines (6 total)

| # | Name | Domain | Role |
|---|------|--------|------|
| 1 | Ingestion Engine | Acquisition | Connect, sync, normalize raw data from sources |
| 2 | Code Intelligence Engine | Acquisition | Parse code structurally (AST, symbols, dependencies) |
| 3 | Knowledge Extraction Engine | Acquisition | Convert information → explicit knowledge with confidence scores |
| 4 | Knowledge Storage Engine | Core | Persist knowledge across 4 storage layers |
| 5 | Retrieval Intelligence Engine | Intelligence | Find relevant knowledge via hybrid retrieval |
| 6 | Context Delivery Engine | Intelligence | Assemble model-ready context packages |

---

## Domains (4 total)

| Domain | Responsibility | Engines |
|--------|----------------|---------|
| **Knowledge Acquisition** | Collect and understand project data | 1, 2, 3 |
| **Knowledge Core** | Store and maintain canonical memory | 4 |
| **Knowledge Intelligence** | Retrieve and reason over knowledge | 5, 6 |
| **Knowledge Consumption** | Deliver knowledge to consumers | — |

---

## Retrieval Strategies

| Strategy | Purpose | Best For |
|----------|---------|----------|
| **Vector** | Semantic similarity search | "Find knowledge about X" |
| **Keyword** | Exact text matching | "Find class PaymentService" |
| **Graph** | Relationship traversal | "What depends on X?" |

### Intent Types (8 total)

| Intent | Example Query | Primary Strategy |
|--------|---------------|------------------|
| `CODE_UNDERSTANDING` | "How does PaymentService work?" | Vector + Graph |
| `REQUIREMENT_TRACEABILITY` | "Which stories implement auth?" | Graph + Keyword |
| `ARCHITECTURE` | "Why did we choose Kafka?" | Vector |
| `IMPACT_ANALYSIS` | "What breaks if I change the DB?" | Graph traversal |
| `BUG_INVESTIGATION` | "Why is checkout failing?" | Keyword + Vector |
| `API_USAGE` | "How do I call the payment API?" | Keyword + Graph |
| `COMPARISON` | "Compare Stripe vs PayPal" | Vector + Keyword |
| `SUMMARY` | "Summarize the payment module" | Vector |

---

## Confidence Tiers

| Tier | Range | Treatment |
|------|-------|-----------|
| **High** | > 0.8 | Rule-based extraction; trust for most queries |
| **Medium** | 0.5 – 0.8 | LLM-assisted extraction; include but flag |
| **Low** | < 0.5 | Ambiguous extraction; mark for human review |

---

## Context Compression Tiers (5 total)

| Tier | Strategy | When Applied |
|------|----------|--------------|
| 1 | Confidence pruning | Remove chunks with confidence < threshold |
| 2 | Lifecycle pruning | Remove UPDATED/SUPERSEDED chunks |
| 3 | Relevance truncation | Keep top-K by relevance_score |
| 4 | Content summarization | Use LLM to condense long chunks |
| 5 | Relationship pruning | Remove low-confidence relationships |

---

## Storage Layers (4 total)

| Layer | Purpose | Dev Tech | Prod Tech |
|-------|---------|----------|-----------|
| **Vector Store** | Semantic similarity search | ChromaDB | pgvector / Weaviate |
| **Graph Store** | Relationship traversal | NetworkX | Neo4j |
| **Metadata Store** | Structured filtering & traceability | SQLite | PostgreSQL |
| **Raw Sources** | Original data preservation | Local FS | S3 |

---

## RBAC Roles (5 total)

| Role | Read | Ingest | Configure | Audit |
|------|------|--------|-----------|-------|
| `ADMIN` | All | All | All | All |
| `ARCHITECT` | All | All | No | Yes |
| `DEVELOPER` | Own projects | Own repos | No | No |
| `VIEWER` | Public only | No | No | No |
| `SERVICE` | Scoped | Scoped | No | No |

---

## Data Classification Levels (4 total)

| Level | Sources | Retention |
|-------|---------|-----------|
| `PUBLIC` | Public repos, public docs | Indefinite |
| `INTERNAL` | Private repos (team), team Confluence | 2 years after project close |
| `CONFIDENTIAL` | Restricted Confluence, proprietary code | Project lifetime + 1 year |
| `RESTRICTED` | HR/Finance docs, security configs | Compliance-driven (7+ years) |

---

## Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Knowledge First** | Model is replaceable, knowledge is permanent |
| **Source Traceability** | Every knowledge traces back to its source via SourceReference |
| **Never Trust Extracted Knowledge Completely** | Confidence scores always attached (0.0–1.0) |
| **Model Independence** | Any LLM can be swapped without changing knowledge core |

---

## Cross-Cutting Capabilities

| Capability | Description |
|------------|-------------|
| **Lifecycle** | 8-state state machine, 14 valid transitions, staleness detection |
| **Traceability** | Every knowledge traces back to source via SourceReference |
| **Governance & Trust** | RBAC (5 roles), audit logging, data classification (4 levels) |
| **Evaluation** | 4 quality dimensions, test protocols, feedback loop |

---

## Engine Components

### RawItem
Normalized raw data from any source before extraction. Contains `item_id`, `source_type`, `title`, `content`, `content_type`, `metadata`, `created_at`, `updated_at`, `tags`.

### SyncManager
Orchestrates incremental sync across all connectors. Manages schedules, detects changes via content hash comparison, and queues items for re-processing.

### CodeEntity
Structured representation of a code element extracted via AST parsing. Contains `id`, `kind` (CLASS, FUNCTION, etc.), `name`, `file_path`, `line_start`, `line_end`, `signature`, `documentation`, `parents`, `children`, `relationships`.

### ModelAdapter
Protocol interface for LLM adapters. Methods: `adapt(context, model_config) -> str`, `parse_response(response) -> dict`, `get_token_limit(model_config) -> int`. Enables model independence.

---

## Retrieval Algorithms

### RRF (Reciprocal Rank Fusion)
Hybrid ranking algorithm that combines results from multiple retrieval strategies. Formula: `score(result) = Σ(1 / (k + rank_in_strategy))` where k is typically 60. Produces robust fused rankings without requiring calibrated scores.

---

## Deployment & Operations

### Production Readiness
Requirements for deploying PKH to production:
- PostgreSQL 16+ with pgvector extension
- Neo4j 5+ (or compatible graph database)
- Object storage (S3, GCS, or MinIO)
- Redis (optional, for caching)
- Load balancer for horizontal scaling

See `docs/deployment-guide.md` for full details.

### Troubleshooting
Common issues and solutions documented in `docs/troubleshooting-guide.md`.
