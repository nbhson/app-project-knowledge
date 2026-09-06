# PKH — Implementation Plan

> **Vision:** Transform fragmented project information into a continuously evolving, connected, model-independent knowledge system.
> **Core tenet:** Knowledge is the long-term asset. Model is a replaceable consumer.

> 📅 **For daily targets and tasks, see [`docs/plan/daily/`](daily/README.md)** — 45 day-by-day files with clear targets to move to the next day. 30-day plan was too tight; 45 days adds buffer for integration, testing, and polish (see Timeline below).

---

## Current Status

> ✅ **Implementation In Progress — `src/` exists (scaffold 06/09, 36 tests, 67.79% coverage).**
> `src/pkh/` đã scaffold (models, config, storage, engines, adapters, CLI, API). `pkh ingest/query` chạy được ở mức MVP Git+Python+rule-only; gaps còn lại tracked trong `docs/plan/fix-plan.md`. Không đánh dấu phase done khi chưa có `pytest` log.

**Project State:** Documentation complete; scaffold implementation done (Phase 0-1 partial). Remaining work per `docs/plan/fix-plan.md` (Phase 0 docs sync → Phase 1 P0 → Phase 2 P1 → Phase 3 P2). Verification gate: no phase is marked done until `pytest` passes for that phase.

This repository contains the complete architectural design and the scaffold implementation for the Project Knowledge Harness (PKH) system. The plan below describes both the documented design and the upcoming hardening phases.

### Completed Artifacts

| Component | Status | Location |
|-----------|--------|----------|
| Vision & Design Principles | ✅ Documented | `docs/core/1-vision-and-design-principles.md` |
| Core Architecture | ✅ Documented | `docs/core/2-architecture.md` |
| Knowledge Model | ✅ Documented | `docs/core/3-knowledge-model.md` |
| Knowledge Lifecycle | ✅ Documented | `docs/core/4-knowledge-lifecycle.md` |
| Source of Truth Model | ✅ Documented | `docs/core/5-source-of-truth-model.md` |
| Retrieval Strategy | ✅ Documented | `docs/core/6-retrieval-strategy.md` |
| Context Contract | ✅ Documented | `docs/core/7-context-contract.md` |
| Evaluation Framework | ✅ Documented | `docs/core/8-evaluation-framework.md` |
| Governance & Trust Model | ✅ Documented | `docs/core/9-governance-and-trust-model.md` |
| Domain Documentation (4) | ✅ Documented | `docs/domains/` |
| Engine Documentation (6) | ✅ Documented | `docs/engines/` |
| Layer Architecture (4) | ✅ Documented | `docs/layers/` |
| Tech Stack Details | ✅ Documented | `docs/tech-stack.md` |
| Project Structure | ✅ Documented (planned layout) | `docs/project-structure.md` |
| Overall Architecture | ✅ Documented | `docs/overall-architecture.md` |
| Deployment Guide | ✅ Documented (spec) | `docs/deployment-guide.md` — requires `src/` to be valid |
| Troubleshooting Guide | ✅ Documented | `docs/troubleshooting-guide.md` |
| Glossary | ✅ Documented | `docs/glossary.md` |
| Decisions (ADRs) | ✅ Documented | `docs/decisions/` |

### Pending Implementation

| Component | Status | Estimated Effort | Verification Gate |
|-----------|--------|------------------|-------------------|
| Python source code (6 engines) | ⏳ Pending | **45 days** (was 30, see phases below) | `pytest tests/` + `ruff check` + `mypy` must pass per phase |
| Test suite | ⏳ Pending | Integrated with implementation | Coverage >80% per engine |
| Configuration examples (`config/settings.yaml.example`) | ⏳ Pending | Part of Phase 0 Day 2 | `pkh init` generates valid YAML |

### Verification Rule (Anti Hallucination)

- Không đánh dấu phase là "done" khi chỉ có docs. Mỗi phase phải có **code + test + log chạy thực tế** (ví dụ: `pytest tests/unit/test_lifecycle.py -v`).
- `README` và `docs` không được claim benchmark (P99 <1000ms, coverage >80%) khi chưa có số liệu từ `pytest --cov` thực tế.

---

## Architecture Overview

```mermaid
graph TD
    D1[Domain 1: Knowledge Acquisition\nEngines 1, 2, 3\nConnect, parse code, extract knowledge]
    D2[Domain 2: Knowledge Core\nEngine 4\nStore & maintain canonical memory]
    D3[Domain 3: Knowledge Intelligence\nEngines 5, 6\nFind and deliver context intelligently]
    D4[Domain 4: Knowledge Consumption\nConsumers\nDeliver to humans, agents, apps]

    KM[KNOWLEDGE MODEL\n23 Entity Types | 15 Relationship Types | 8 Lifecycle States\nSourceReference Model 5 source types]

    ENG[6 EXECUTION CAPABILITIES\n① Ingestion → ② Code Intelligence → ③ Extraction\n④ Storage → ⑤ Retrieval → ⑥ Context Delivery]

    CC[CROSS-CUTTING CAPABILITIES\nLifecycle | Traceability | Governance & Trust | Evaluation]

    D1 & D2 & D3 & D4 --> KM
    KM --> ENG
    ENG --> CC
```

---

## Timeline 45 Ngày — Tổng quan

> **Điều chỉnh từ 30 → 45 ngày:** Thêm 15 ngày buffer cho integration, testing, và harden. MVP giữ 10 ngày để có demo sớm.

```
Week 1 (Day 1-7)    ███████ Phase 0-1 Foundation + Ingestion (Git)
Week 2 (Day 8-14)   ███████ Phase 2 Code Intelligence (Python) + buffer
Week 3 (Day 15-21)  ███████ Phase 3 Extraction (rule → LLM)
Week 4 (Day 22-28)  ███████ Phase 4 Storage (outbox + reconciler)
Week 5 (Day 29-34)  ██████  Phase 5 Retrieval (RRF) + Phase 6 Context (adapters)
Week 6 (Day 35-40)  ██████  Phase 7 CLI/API + Phase 8 Integration
Week 7 (Day 41-45)  █████   Phase 9 Hardening & Evaluation (buffer, không cắt)
```

| Phase | Days | Duration | Nối tiếp 30-ngày cũ |
|-------|------|----------|---------------------|
| 0 Foundation | 1-3 | 3d (was 2) | +1 buffer cho config & error hierarchy |
| 1 Ingestion | 4-10 | 7d (was 5) | +2 cho Confluence/Jira connector |
| 2 Code Intelligence | 11-15 | 5d (was 4) | +1 buffer cho benchmark |
| 3 Extraction | 16-21 | 6d (was 4) | +2 cho LLM cost/calibration |
| 4 Storage | 22-28 | 7d (was 4) | +3 cho outbox/reconciler/nightly check |
| 5 Retrieval | 29-34 | 6d (was 4) | +2 cho RRF tuning |
| 6 Context Delivery | 34-36 | 3d (was 3) | giữ nguyên |
| 7 CLI/API | 37-41 | 5d (was 3) | +2 cho RBAC & error handling |
| 8 Integration | 42-43 | 2d (was 1) | +1 cho e2e |
| 9 Hardening | 44-45 | 2d (was 1) | +1 buffer; không cắt polish như 30-day |

**Tổng: 45 ngày** (thay vì 30). Nếu vượt 45, cắt scope Full (multi-lang, Neo4j/S3) thay vì kéo dài.

## MVP Scope — Anti Over-Engineering

> **Rủi ro:** 6 engines + 4 stores + 8 states ngay từ đầu dễ dẫn đến 30 ngày không kịp và không có gì chạy được để demo.

**Nguyên tắc:** MVP **Day 1-10** phải cho ra `pkh query` chạy được trên 1 repo Git local. Full 45 ngày chỉ mở rộng từ MVP, không làm lại.

| Track | Scope | Stores | Sources | Retrieval | Tiêu chí done |
|-------|-------|--------|---------|-----------|---------------|
| **MVP (Day 1-10)** | E1(Git only) → E2(Python only) → E3(rule-based only) → E4(SQLite + Chroma + NetworkX) → E5(vector-only) → E6(MockAdapter) | 3 layers (Metadata SQLite, Vector Chroma, Graph NetworkX) — Raw = local FS | Git local filesystem | Vector-only (không RRF, không graph traversal — thống nhất với adr-005) | `pkh ingest --source git://./sample && pkh query "what is PaymentService?"` trả về ContextPackage có sources, `pytest tests/unit -q` pass |
| **Full (Day 11-45)** | Thêm Confluence/Jira/Docs, đa ngôn ngữ, LLM enrichment, RRF hybrid, Neo4j/pgvector/S3, RBAC, API, 5-tier compression | 4 layers đầy đủ | Git + Confluence + Jira + Docs + API Specs | Hybrid RRF + Reranking + Deduplication | Đạt mọi Success Criteria ở cuối plan |

**Quy tắc triển khai:**
1. Không implement Confluence/Jira connector trước khi Git connector có test pass.
2. Không thêm Neo4j/pgvector trước khi SQLite+Chroma+NetworkX chạy ổn.
3. Mỗi engine phải có `MockAdapter` / fake store để test không cần API key hay Docker.
4. Nếu MVP trễ > Day 12, cắt Full scope (bỏ multi-lang, giữ Python-only) thay vì kéo dài MVP — buffer 45 ngày đã tính.

---

## Phase 0 — Foundation (Day 1–3) — +1 buffer vs 30-day

### Goal

Set up project structure, Knowledge Model, and core types.

### Day 1 — Project Scaffolding

- [ ] Initialize Python project with pyproject.toml, requirements.txt
- [ ] Create package structure: `src/pkh/` with:
  ```
  pkh/
  ├── __init__.py
  ├── models/           # KnowledgeObject, SourceReference, enums
  ├── config/           # YAML config parsing
  ├── engines/          # Engine 1-6 implementations
  │   ├── ingestion/
  │   ├── code_intelligence/
  │   ├── extraction/
  │   ├── storage/
  │   ├── retrieval/
  │   └── context_delivery/
  ├── adapters/         # LLM adapters (OpenAI, Claude, etc.)
  ├── storage/          # Vector, Graph, Metadata backends
  ├── cli/              # Typer CLI commands
  └── utils/            # Logging, error handling, helpers
  ```
- [ ] Set up testing framework (pytest)
- [ ] Define core Pydantic models:
  - `LifecycleState` enum: DISCOVERED, EXTRACTED, VALIDATING, ACTIVE, UPDATED, SUPERSEDED, DEPRECATED, ARCHIVED
  - `ObjectType` enum: ENTITY, RELATIONSHIP, DECISION, RULE
  - `EntityType` enum: 23 types (REPOSITORY, MODULE, PACKAGE, FILE, CLASS, INTERFACE, FUNCTION, METHOD, ENUM, TYPE, VARIABLE, EPIC, STORY, TASK, BUG, REQUIREMENT, ADR, DOCUMENT, API_SPEC, ENDPOINT, etc.)
  - `RelationshipType` enum: 15 types (IMPLEMENTS, DEPENDS_ON, CALLS, USES, OWNS, DOCUMENTS, REQUIRES, SUPERSEDES, RELATED_TO, AFFECTS, PART_OF, TRACES_TO, CONTAINS, EXTENDS, IMPLEMENTS_IFACE)
  - `SourceType` enum: GIT, CONFLUENCE, JIRA, DOCUMENT, API_SPEC
- [ ] Set up logging infrastructure (structured logging with JSON output)

### Day 2-3 — Knowledge Model and Config (buffer Day 3 cho error hierarchy + config validation)

- [ ] Implement `KnowledgeObject` Pydantic model with full validation:
  - id (UUID v4), object_type, title, description, content, source_references (required, non-empty), confidence (0.0-1.0), lifecycle_state, created_at, updated_at, tags, properties
- [ ] Implement `SourceReference` model with source-specific fields:
  - source_type, source_id, url, title, last_synced, extra (dict with type-specific keys)
- [ ] Implement lifecycle state machine with transition validation:
  - 14 valid transitions defined in `core/4-knowledge-lifecycle.md`
- [ ] Implement Config class with YAML parsing:
  - sources config (git, confluence, jira, documents)
  - storage config (vector, graph, metadata providers)
  - retrieval config (strategies, fusion weights)
  - adapters config (model selection)
  - governance config (RBAC settings)
- [ ] Write unit tests for model validation
- [ ] Setup error handling infrastructure with custom exception hierarchy

**Deliverable:** Project scaffold with typed knowledge model, config system, test framework

---




## Phase 1 — Ingestion Engine (Day 4–10) — +2 buffer

### Goal

Build Engine 1: Connect to Git, Confluence, Jira; detect changes; normalize raw data into KnowledgeObject s.

### Day 4 — Git Connector

- [ ] Implement GitSourceConnector -- clone/pull repo, list files, track changes via git log
- [ ] Implement FileWatcher -- detect new/modified/deleted files since last sync
- [ ] Normalize git data -> KnowledgeObject (Repository, Module, File entities)
- [ ] Add auth: SSH key, token, username/password

### Day 5 — Confluence Connector

- [ ] Implement ConfluenceSourceConnector -- fetch pages by space, recurse children
- [ ] Parse Confluence storage format -> markdown/text
- [ ] Detect ADRs, design docs, specs by content patterns
- [ ] Normalize -> KnowledgeObject (Document, ArchitectureDecision, Requirement entities)
- [ ] Track page version history for change detection

### Day 6 — Jira Connector

- [ ] Implement JiraSourceConnector -- fetch issues by project key, filter by type
- [ ] Parse issue fields: title, description, acceptance criteria, comments, transitions
- [ ] Build requirement graph: Epic -> Story -> Task -> Sub-task
- [ ] Normalize -> KnowledgeObject (Epic, Story, Task, Bug, Requirement entities)
- [ ] Track status changes for lifecycle updates

### Day 7-8 — Document Connector and Change Detection (2d, +1 buffer)

- [ ] Implement DocumentSourceConnector -- local filesystem + URL-based docs
- [ ] Support: Markdown, PDF (text extraction), OpenAPI specs, DB schema files
- [ ] Implement SyncManager -- orchestrates all connectors with incremental sync
- [ ] Implement ChangeDetector -- diff-based: what changed since last ingestion
- [ ] Webhook listener for real-time updates (Git push, Confluence edit, Jira transition)

### Day 9-10 — Ingestion CLI and Integration Tests (2d buffer cho integration)

- [ ] CLI: pkh ingest --source git://path --source confluence://SPACE --source jira://PROJECT
- [ ] CLI: pkh ingest --sync (incremental)
- [ ] Write integration tests for each connector (mocked API calls)
- [ ] Add progress tracking + logging

**Deliverable:** Engine 1 fully functional, 3 connectors working, CLI command pkh ingest

---

## Phase 2 — Code Intelligence Engine (Day 11–15) — +1 buffer

### Goal

Build Engine 2: Parse source code structurally — AST, symbols, dependencies, call graphs. Uses tree-sitter for language-agnostic parsing.

### Supported Languages — Incremental (MVP: Python only)

| Language | Parser | Classes | Functions | Imports | Interfaces | Phase |
|----------|--------|---------|-----------|---------|------------|-------|
| **Python** | tree-sitter-python | ✓ | ✓ | ✓ | ✗ | **MVP Day 8** |
| TypeScript | tree-sitter-typescript | ✓ | ✓ | ✓ | ✓ | Post-MVP |
| Java | tree-sitter-java | ✓ | ✓ | ✓ | ✓ | Later |
| Go | tree-sitter-go | ✓ | ✓ | ✓ | ✗ | Later |
| Rust | tree-sitter-rust | ✓ | ✓ | ✓ | ✓ | Later |
| C/C++ | tree-sitter-cpp | ✓ | ✓ | ✓ | ✓ | Later |

### Day 11 — AST Parser Foundation

- [ ] Implement `CodeParser` using `tree-sitter` — language-agnostic base
- [ ] Python support via `tree-sitter-python` (classes, functions, imports, decorators)
- [ ] Extract: Class definitions, method signatures, inheritance, interfaces
- [ ] Build symbol table per file
- [ ] Output: Structured code knowledge → `KnowledgeObject` (Class, Function, Interface entities)
- [ ] Handle parse errors gracefully with fallback to text-based extraction

### Day 12 — Dependency & Call Graph

- [ ] Implement `DependencyAnalyzer` — imports → module dependencies (DEPENDS_ON relationships)
- [ ] Implement `CallGraphBuilder` — function A calls function B (cross-file) (CALLS relationships)
- [ ] Build inter-file dependency map
- [ ] Detect circular dependencies
- [ ] Output: `KnowledgeObject` with DEPENDS_ON, CALLS relationships
- [ ] Cross-file analysis for multi-module projects

### Day 13 — Code Knowledge Enrichment

- [ ] Map code entities to Jira requirements (regex: `JIRA-123`, `#123` in comments)
- [ ] Map code entities to Confluence docs (links in docstrings, README refs)
- [ ] Tag code with architectural context (module boundaries, package structure)
- [ ] Generate code knowledge embeddings (semantic description of each entity)
- [ ] Cross-link: Code ↔ Requirement ↔ Document
- [ ] Entity enrichment: CLASS, INTERFACE, FUNCTION, METHOD, ENUM, TYPE, VARIABLE

### Day 14-15 — Code Engine Tests & Integration (2d, +1 buffer cho benchmark)

- [ ] Test parser on sample Python/TypeScript/Java projects
- [ ] Validate call graph accuracy against known patterns
- [ ] Verify cross-linking with Jira/Confluence references
- [ ] Benchmark: parsing speed for 10k+ line projects (< 1 min for typical project)
- [ ] Integrate with Ingestion Engine pipeline

**Deliverable:** Engine 2 fully functional, AST-based code understanding, dependency/call graphs, cross-linking

---

## Phase 3 — Knowledge Extraction Engine (Day 16–21) — +2 buffer cho LLM calibration

### Goal

Build Engine 3: Convert raw ingested data into explicit, structured knowledge with entities, relationships, decisions, rules. Implements 3-pass hybrid pipeline.

### Day 16 — Entity & Relationship Extraction (Rule-Based)

- [ ] Implement `EntityExtractor` — regex + pattern matching for entities
  - Code entities: classes, functions, imports from AST
  - Document entities: headings, lists, tables
  - Requirement entities: epics, stories, tasks from Jira structure
- [ ] Implement `RelationshipExtractor` — rule-based mappings:
  - `implements` → IMPLEMENTS
  - `import` / `from X import` → DEPENDS_ON
  - `class X extends Y` → EXTENDS
  - `class X implements Y` → IMPLEMENTS_IFACE
  - `JIRA-123` reference → TRACES_TO
  - `ADR-001` reference → DOCUMENTS
- [ ] Confidence scoring: high (1.0) for structural (code), medium (0.7) for inferred

### Day 17-18 — LLM-Powered Extraction (Model-Agnostic) (2d, +1 buffer)

- [ ] Define `ExtractionPromptTemplate` — language-agnostic prompts with Jinja2
- [ ] Implement `LLMExtractionAdapter` interface with pluggable implementations
- [ ] Implement `OpenAIAdapter` as default; easily swappable to Claude/Gemini/local
- [ ] Implement `MockAdapter` for testing
- [ ] LLM prompts for: entity identification, relationship inference, decision detection
- [ ] Structured output parsing with JSON mode / regex fallback

### Day 19 — Decision & Rule Detection

- [ ] Implement `ADRDetector` — pattern matching for Architecture Decision Records:
  - Pattern: `ADR-*`, `Decision Record`, `Context/Decision/Consequences` structure
- [ ] Implement `BusinessRuleDetector` — detect "must", "should", "cannot", "required" patterns
- [ ] Implement `ConstraintDetector` — technical constraints, NFRs, security requirements
- [ ] Output: KnowledgeObjects with object_type=DECISION or RULE

### Day 20-21 — Extraction Pipeline & Validation (2d, +1 buffer cho calibration)

- [ ] Build 3-pass pipeline: Rule-based → LLM enrichment → Confidence scoring
- [ ] Implement `KnowledgeValidator` — orphan detection, duplicates, staleness
- [ ] Auto-supersede: new conflicting knowledge → mark old as SUPERSEDED
- [ ] Validation quality gates from `domains/knowledge-acquisition.md`:
  - Source reference present (required)
  - Content non-empty
  - Confidence assigned (0.0-1.0)
  - Lifecycle state valid
- [ ] Write tests with golden data
- [ ] Implement conflict resolution per `core/5-source-of-truth-model.md`

**Deliverable:** Engine 3 fully functional, hybrid rule+LLM extraction, confidence scoring, validation pipeline

---

## Phase 4 — Knowledge Storage Engine (Day 22–28) — +3 buffer cho outbox/reconciler

### Goal

Build Engine 4: Persistent storage across Vector, Graph, and Metadata layers with full traceability. Implements 4-layer architecture per `core/3-knowledge-model.md`.

### Day 22-23 — Metadata Store (SQLAlchemy + SQLite) + outbox table (2d)

- [ ] Define DB schema (SQLite for dev, PostgreSQL for prod):
  - `knowledge_objects` — id, object_type, title, description, content, source_references (JSON), confidence, lifecycle_state, created_at, updated_at, tags (JSON), properties (JSON)
  - `sources` — source_id, source_type, url, title, last_synced, content_hash
  - `knowledge_sources` — junction table linking knowledge_objects to sources
  - `relationships` — from_id, to_id, relationship_type, confidence
  - `lifecycle_events` — knowledge_id, from_state, to_state, triggered_at, trigger_reason
- [ ] Implement `MetadataStore` — CRUD with full traceability queries
- [ ] Lifecycle state filtering (exclude DEPRECATED, ARCHIVED from active queries)
- [ ] Source reference integrity checks

### Day 24 — Vector Store (ChromaDB) + idempotency

- [ ] Implement `VectorStore` interface (provider-agnostic):
  - `upsert(knowledge_chunks: list[KnowledgeChunk]) -> None`
  - `query(query_embedding, top_k, filters) -> list[ScoredChunk]`
  - `delete(ids: list[str]) -> None`
  - `exists(id: str) -> bool`
- [ ] Implement `ChromaDBBackend` as default
- [ ] Implement `EmbeddingGenerator` with OpenAI adapter
- [ ] Chunk knowledge by entity type (512 tokens per chunk, 64 token overlap)
- [ ] Store knowledge + metadata as vectors with filterable attributes (entity_type, lifecycle_state, source_type)

### Day 25 — Graph Store (NetworkX) + outbox fan-out

- [ ] Implement `GraphStore` interface:
  - `add_node(entity_id, entity_type, properties)`
  - `add_edge(from_id, to_id, relationship_type, confidence)`
  - `get_neighbors(entity_id, relationship_types, max_depth)`
  - `shortest_path(from_id, to_id)`
  - `subgraph(entity_ids)`
  - `detect_communities()`
- [ ] Build full graph: nodes = knowledge objects, edges = relationships
- [ ] Operations: neighbors, shortest_path, subgraph, community detection
- [ ] Cross-store sync: metadata changes → graph updates
- [ ] Lifecycle-aware: exclude DEPRECATED/SUPERSEDED nodes from traversal

### Day 26-28 — Storage Integration & Reconciler (3d, +2 buffer cho nightly check & benchmarks)

- [ ] Implement `KnowledgeStore` — unified interface over all 3 stores:
  ```python
  class KnowledgeStore:
      async def save(self, knowledge: KnowledgeObject) -> None
      async def get(self, id: str) -> KnowledgeObject | None
      async def search(self, query: str, filters: dict) -> list[KnowledgeObject]
      async def get_by_source(self, source_id: str) -> list[KnowledgeObject]
      async def get_relationships(self, entity_id: str) -> list[Relationship]
      async def delete(self, id: str) -> None
  ```
- [ ] Composite queries: "find all code related to JIRA-123"
- [ ] Backup/restore via JSON serialization
- [ ] Performance benchmarks:
  - Write throughput: > 1000 ops/sec
  - Read latency: < 50ms for single entity, < 200ms for composite query

**Deliverable:** Engine 4 fully functional, 4-layer persistence, unified query interface, traceability guaranteed

---

## Phase 5 — Retrieval Intelligence Engine (Day 29–34) — +2 buffer

### Goal

Build Engine 5: Intelligent query processing — intent detection, hybrid retrieval, graph traversal, reranking with RRF fusion.

### Day 29-30 — Intent Detection & Query Planning (2d)

- [ ] Implement `IntentClassifier` — classify queries into 8 intent types:
  - CODE_UNDERSTANDING: "How does PaymentService work?"
  - REQUIREMENT_TRACEABILITY: "Which stories implement auth?"
  - ARCHITECTURE: "Why did we choose Kafka?"
  - IMPACT_ANALYSIS: "What breaks if I change the payment DB?"
  - BUG_INVESTIGATION: "Why is checkout failing?"
  - API_USAGE: "How do I call the payment API?"
  - COMPARISON: "Compare Stripe vs PayPal"
  - SUMMARY: "Summarize the payment module"
- [ ] Implement `QueryPlanner` — decompose complex queries:
  - Multi-part: "What depends on X and what does X depend on?"
  - Temporal: "What changed in the auth module last week?"
- [ ] Strategy selection matrix per `core/6-retrieval-strategy.md`

### Day 31 — Hybrid Retrieval (RRF)

- [ ] Implement `HybridRetriever` — parallel execution of 3 strategies:
  - **Vector search**: semantic similarity via embeddings
  - **Keyword search**: full-text inverted index
  - **Graph traversal**: relationship-based discovery
- [ ] Score fusion with Reciprocal Rank Fusion (RRF):
  ```python
  score(result) = sum(1 / (k + rank_in_strategy) for strategy in strategies)
  ```
  where k = 60 (default)
- [ ] Configurable weights per intent type
- [ ] Each strategy has timeout (200ms) and returns partial results

### Day 32 — Graph Traversal & Reranking

- [ ] Implement `GraphTraverser` — BFS/DFS with configurable depth limit (default 3 hops)
- [ ] Implement `Reranker` — weighted scoring:
  - confidence_weight: 0.3
  - lifecycle_weight: 0.2 (ACTIVE > UPDATED > others)
  - recency_weight: 0.1 (prefer recently updated)
  - relevance_weight: 0.4 (query relevance score)
- [ ] Implement `Deduplicator` — merge overlapping results, keep highest confidence
- [ ] Lifecycle filtering: exclude SUPERSEDED, DEPRECATED, ARCHIVED by default

### Day 33-34 — Retrieval Pipeline & Tests (2d buffer cho golden queries)

- [ ] Complete pipeline: Query → Intent → Plan → Hybrid Retrieve → Traverse → Rerank → Results
- [ ] Retrieval metrics implementation:
  - precision@k, recall@k, NDCG
- [ ] Benchmark: < 500ms for 10K knowledge objects
- [ ] Write tests with golden queries and expected results
- [ ] Implement fallback strategies (vector-only if graph unavailable)

**Deliverable:** Engine 5 fully functional, hybrid retrieval with intent detection and RRF fusion, < 500ms latency

---

## Phase 6 — Context Delivery Engine (Day 35–37)

### Goal

Build Engine 6: Assemble retrieval results into model-ready context packages with universal contract. Every output follows `ContextPackage` schema.

### Day 35 — Context Assembly

- [ ] Define `ContextPackage` Pydantic model (from `core/7-context-contract.md`):
  - query, knowledge (list of KnowledgeChunk), relationships (list of RelationshipChunk)
  - confidence, sources, lifecycle_states, warnings, intent, search_stats
- [ ] Implement `ContextAssembler` — group, enrich, attach source refs
- [ ] Implement `ContextCompressor` — smart trimming for context limits:
  - Tier 1: Confidence-based pruning (remove < threshold)
  - Tier 2: Lifecycle-based pruning (remove UPDATED/SUPERSEDED)
  - Tier 3: Relevance-based truncation (keep top-K)
  - Tier 4: Content compression (summarize long chunks)
  - Tier 5: Relationship pruning (remove low-confidence edges)
- [ ] Token counting with tiktoken for accurate context window estimation

### Day 36 — Model Adapters (Model Independence)

- [ ] Define `ModelAdapter` interface:
  ```python
  class ModelAdapter(Protocol):
      async def complete(self, context: ContextPackage, model_config: dict) -> str
      def format_context(self, context: ContextPackage) -> str
      def parse_response(self, response: str) -> dict
      def get_token_limit(self, model_config: dict) -> int
  ```
- [ ] Implement `ClaudeAdapter` — system prompt + messages array
- [ ] Implement `GPTAdapter` — JSON instructions + messages + tools
- [ ] Implement `GeminiAdapter` — text with examples
- [ ] Implement `LocalLLMAdapter` — plain text format
- [ ] Implement `MockAdapter` for testing
- [ ] Config-driven: `adapters.default = "openai"` — switch by editing config only

### Day 37 — Context Contract & Streaming

- [ ] Implement `ContextValidator` — validate output against contract:
  - All chunks have SourceReference
  - All confidence scores are valid (0.0-1.0)
  - Lifecycle states are included
- [ ] Streaming support for long contexts
- [ ] Context caching with TTL
- [ ] Rate limiting per model adapter
- [ ] SLA enforcement: token limit, latency, determinism guarantees

**Deliverable:** Engine 6 fully functional, model-agnostic adapters, universal context contract, 5-tier compression

---

## Phase 7 — CLI, API & Integration (Day 38–42) — +2 buffer

### Goal

Wrap all engines into a usable CLI and REST API. Connect everything into a coherent system with governance enforcement.

### Day 38-39 — CLI Interface (2d)

- [ ] `pkh init` — scaffold project config with all sections
- [ ] `pkh ingest` — full ingestion pipeline with progress tracking
- [ ] `pkh query "question"` — natural language query with intent display
- [ ] `pkh context --query "..."` — raw context package for AI agents
- [ ] `pkh graph --entity "Name"` — visualize knowledge graph (ASCII/JSON)
- [ ] `pkh sync` — incremental sync with change report
- [ ] `pkh status` — ingestion status, counts, freshness, governance violations
- [ ] `pkh audit` — view audit log (ADMIN/ARCHITECT role required)

### Day 40-41 — REST API + RBAC (2d)

- [ ] FastAPI app with endpoints:
  - `POST /ingest` — trigger ingestion
  - `GET /ingest/status` — check ingestion status
  - `POST /query` — natural language query
  - `POST /context` — get context package
  - `GET /knowledge/{id}` — get knowledge object with full traceability
  - `GET /graph/explore` — explore knowledge graph
  - `GET /sources/status` — check source sync status
  - `GET /health` — health check with component status
  - `GET /audit` — audit log (ADMIN/ARCHITECT only)
- [ ] OpenAPI spec with auto-generated documentation
- [ ] Auth middleware with RBAC enforcement:
  - ADMIN: full access
  - ARCHITECT: read all, trigger re-extraction, view audit
  - DEVELOPER: read own projects, run ingestion
  - VIEWER: read-only public knowledge
  - SERVICE: programmatic access, scoped
- [ ] Request/response validation with Pydantic models

### Day 42 — End-to-End Integration

- [ ] Full pipeline test: Ingest → Extract → Store → Retrieve → Context → Answer
- [ ] Error handling:
  - Partial ingestion (some sources fail, others succeed)
  - Source API failures with retry
  - Rate limit handling
  - Graceful degradation (fallback to vector-only if graph unavailable)
- [ ] Health checks for all components
- [ ] Structured logging with correlation IDs
- [ ] Integration with governance: audit every operation

**Deliverable:** Complete CLI + API, end-to-end pipeline working, RBAC enforcement, audit logging

---

## Phase 8 — Evaluation, Docs & Polish (Day 43–44) — +1 buffer

### Goal

Validate quality per `core/8-evaluation-framework.md`, write documentation, prepare for production use.

### Day 43 — Evaluation Framework (chạy thực tế)

- [ ] Run evaluation framework:
  - **Knowledge quality**: coverage %, entity accuracy, relationship completeness
  - **Retrieval quality**: precision@k, recall@k, NDCG on test set
  - **Context quality**: token efficiency, source coverage, confidence calibration
  - **System quality**: latency, availability, error rate
- [ ] Compare against targets from `core/8-evaluation-framework.md`:
  - Knowledge coverage: > 80%
  - Retrieval precision@5: > 0.85
  - Context fit rate: > 95%
  - P99 latency: < 1000ms
- [ ] Write user guide: setup, configuration, CLI usage, API reference
- [ ] Write API reference with OpenAPI spec
- [ ] Create example project with sample data
- [ ] Add `.env.example`, configuration templates for all engines
- [ ] Final README + MIT license
- [ ] Run feedback loop test: query → answer → rate → improve

### Day 44 — Docs & Example Project

- [ ] Final README + MIT license polish (cập nhật status 45-day)
- [ ] `.env.example`, `config/settings.yaml.example` hoàn chỉnh
- [ ] Example project với sample data + golden queries

---

## Phase 9 — Hardening & Buffer (Day 45) — NEW, không có trong 30-day

### Goal

Buffer cuối để không trễ deadline. Nếu các phase trước trễ, dùng Day 45 để fix thay vì kéo dài thêm.

### Day 45 — Hardening

- [ ] Bugfix tồn đọng từ Phase 0-8
- [ ] `pytest --cov` đạt >80% per engine, `ruff check` + `mypy` clean
- [ ] Load test: 10k knowledge objects, P99 <1000ms (nếu chưa đạt thì ghi rõ gap, không fake số)
- [ ] Demo e2e: `pkh ingest --source git://./sample && pkh query "how does X work?"` có video/log
- [ ] Tag `v0.1.0-mvp` nếu MVP Done, hoặc `v0.1.0` nếu Full Done

**Deliverable:** Release tag + changelog + known limitations (thẳng thắn ghi gì chưa làm được)

---

## Key Architectural Decisions

> **Chi tiết rationale đầy đủ trong `docs/decisions/` (ADRs). Bảng dưới là tóm tắt.**

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Language | Python 3.10+ | Rich ecosystem for NLP, AST, LLM | `docs/decisions/adr-001-language-and-modeling.md` |
| Knowledge Model | Pydantic v2 | Strong typing, validation, serialization | `adr-001` |
| Vector Store | ChromaDB (dev) / pgvector (prod) | Dev zero-config, prod ACID + pgvector scale | `docs/decisions/adr-002-storage.md` |
| Graph Store | NetworkX (dev) / Neo4j (prod) | Dev pure Python, prod clustering | `adr-002` |
| Metadata Store | SQLite (dev) / PostgreSQL (prod) | Dev zero-admin, prod reliability | `adr-002` |
| Raw Store | Local FS (dev) / S3 (prod) | Dev simple, prod durable | `adr-002` |
| Code Parsing | tree-sitter (Python-first) | Language-agnostic, incremental; Python MVP first | `docs/decisions/adr-003-code-parsing.md` |
| LLM Adapters | Strategy pattern + config | True model independence | `docs/decisions/adr-004-llm-adapter.md` |
| CLI | Typer + Rich | Type-safe CLI, beautiful output | `adr-001` |
| API | FastAPI | Async, auto-docs, fast | `adr-001` |
| Fusion | Reciprocal Rank Fusion (RRF k=60) | Proven hybrid ranking, no score calibration | `docs/decisions/adr-005-retrieval.md` |
| Auth | RBAC with JWT/OAuth2 | Granular access control | `adr-004` |

## Risk Mitigation

| Risk | Mitigation | Doc |
|------|------------|-----|
| **Zero code (design-only)** | Verification gate: phase done = `pytest` pass + log chạy thực tế; status tracked in `docs/plan/plan.md#current-status` + `docs/plan/fix-plan.md` | `plan.md#current-status`, `README.md` |
| **Over-engineering (6 engines + 4 stores cùng lúc)** | MVP Day 1-10 (Git+Python+rule+3 stores+vector-only+Mock) trước Full 45 ngày; nếu MVP trễ > Day 12 thì cắt multi-lang | `plan.md#mvp-scope`, `overall-architecture.md` |
| **Polyglot sync (4 stores lệch)** | Metadata là truth, outbox + idempotency + reconciler + nightly check; fail-open read | `engines/knowledge-storage-engine.md#write-path`, `decisions/adr-002-storage.md` |
| LLM API costs & over-confidence | `llm_enabled=false` mặc định, batching, cache `hash(content)`, budget 50k tokens/run, calibration + ECE <0.1 | `engines/knowledge-extraction-engine.md#cost-control`, `decisions/adr-004-llm-adapter.md`, `core/8-evaluation-framework.md` |
| Source API rate limits | Caching, incremental sync, retry exponential backoff, token bucket per connector | `engines/ingestion-engine.md` |
| Knowledge drift / Stale knowledge | Lifecycle 8-state + 14 transitions, staleness >7d warn >30d prompt, auto SUPERSEDED | `core/4-knowledge-lifecycle.md` |
| Context overflow | 5-tier compression + tiktoken counting, `compression_log` | `engines/context-delivery-engine.md` |
| Model lock-in | Strategy `ModelAdapter` + MockAdapter, swap bằng config | `decisions/adr-004-llm-adapter.md` |
| Large codebase / multi-lang complexity | Python-first MVP, plugin per language, chunked + incremental AST, fallback regex | `engines/code-intelligence-engine.md`, `decisions/adr-003-code-parsing.md` |
| Docs duplication | `overall-architecture.md` (big-picture) vs `core/2-architecture.md` (engine deep-dive) scope note; README dedup | `project-structure.md`, `overall-architecture.md`, `core/2-architecture.md` |
| Thiếu rationale cho tech choices | 5 ADRs trong `docs/decisions/` | `decisions/` |
| Security exposure | RBAC 5 roles + source-level permission inheritance + audit hash chain | `core/9-governance-and-trust-model.md` |

## Success Criteria

- [ ] Can ingest from Git, Confluence, Jira, Documents simultaneously
- [ ] Can query natural language and get traceable answers
- [ ] Can swap LLM model by changing config only
- [ ] Every piece of knowledge traces back to source (SourceReference required)
- [ ] Knowledge lifecycle enforced (no stale active knowledge, automatic SUPERSEDED)
- [ ] CLI works end-to-end: `pkh ingest` → `pkh query`
- [ ] API serves context packages for AI agents
- [ ] Retrieval latency < 500ms for 10K knowledge objects
- [ ] Knowledge coverage > 80% of project entities
- [ ] RBAC enforced: users can only access what they can access in source systems
- [ ] Audit log captures all operations with immutability guarantee

