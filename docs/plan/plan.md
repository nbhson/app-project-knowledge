# PKH — 30-Day Implementation Plan

> **Vision:** Transform fragmented project information into a continuously evolving, connected, model-independent knowledge system.
> **Core tenet:** Knowledge is the long-term asset. Model is a replaceable consumer.

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

## Phase 0 — Foundation (Day 1–2)

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

### Day 2 — Knowledge Model and Config

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




## Phase 1 — Ingestion Engine (Day 3–7)

### Goal

Build Engine 1: Connect to Git, Confluence, Jira; detect changes; normalize raw data into KnowledgeObject s.

### Day 3 — Git Connector

- [ ] Implement GitSourceConnector -- clone/pull repo, list files, track changes via git log
- [ ] Implement FileWatcher -- detect new/modified/deleted files since last sync
- [ ] Normalize git data -> KnowledgeObject (Repository, Module, File entities)
- [ ] Add auth: SSH key, token, username/password

### Day 4 — Confluence Connector

- [ ] Implement ConfluenceSourceConnector -- fetch pages by space, recurse children
- [ ] Parse Confluence storage format -> markdown/text
- [ ] Detect ADRs, design docs, specs by content patterns
- [ ] Normalize -> KnowledgeObject (Document, ArchitectureDecision, Requirement entities)
- [ ] Track page version history for change detection

### Day 5 — Jira Connector

- [ ] Implement JiraSourceConnector -- fetch issues by project key, filter by type
- [ ] Parse issue fields: title, description, acceptance criteria, comments, transitions
- [ ] Build requirement graph: Epic -> Story -> Task -> Sub-task
- [ ] Normalize -> KnowledgeObject (Epic, Story, Task, Bug, Requirement entities)
- [ ] Track status changes for lifecycle updates

### Day 6 — Document Connector and Change Detection

- [ ] Implement DocumentSourceConnector -- local filesystem + URL-based docs
- [ ] Support: Markdown, PDF (text extraction), OpenAPI specs, DB schema files
- [ ] Implement SyncManager -- orchestrates all connectors with incremental sync
- [ ] Implement ChangeDetector -- diff-based: what changed since last ingestion
- [ ] Webhook listener for real-time updates (Git push, Confluence edit, Jira transition)

### Day 7 — Ingestion CLI and Integration Tests

- [ ] CLI: pkh ingest --source git://path --source confluence://SPACE --source jira://PROJECT
- [ ] CLI: pkh ingest --sync (incremental)
- [ ] Write integration tests for each connector (mocked API calls)
- [ ] Add progress tracking + logging

**Deliverable:** Engine 1 fully functional, 3 connectors working, CLI command pkh ingest

---

## Phase 2 — Code Intelligence Engine (Day 8–11)

### Goal

Build Engine 2: Parse source code structurally — AST, symbols, dependencies, call graphs. Uses tree-sitter for language-agnostic parsing.

### Supported Languages

| Language | Parser | Classes | Functions | Imports | Interfaces |
|----------|--------|---------|-----------|---------|------------|
| Python | tree-sitter-python | ✓ | ✓ | ✓ | ✗ |
| TypeScript | tree-sitter-typescript | ✓ | ✓ | ✓ | ✓ |
| Java | tree-sitter-java | ✓ | ✓ | ✓ | ✓ |
| Go | tree-sitter-go | ✓ | ✓ | ✓ | ✗ |
| Rust | tree-sitter-rust | ✓ | ✓ | ✓ | ✓ |
| C/C++ | tree-sitter-cpp | ✓ | ✓ | ✓ | ✓ |

### Day 8 — AST Parser Foundation

- [ ] Implement `CodeParser` using `tree-sitter` — language-agnostic base
- [ ] Python support via `tree-sitter-python` (classes, functions, imports, decorators)
- [ ] Extract: Class definitions, method signatures, inheritance, interfaces
- [ ] Build symbol table per file
- [ ] Output: Structured code knowledge → `KnowledgeObject` (Class, Function, Interface entities)
- [ ] Handle parse errors gracefully with fallback to text-based extraction

### Day 9 — Dependency & Call Graph

- [ ] Implement `DependencyAnalyzer` — imports → module dependencies (DEPENDS_ON relationships)
- [ ] Implement `CallGraphBuilder` — function A calls function B (cross-file) (CALLS relationships)
- [ ] Build inter-file dependency map
- [ ] Detect circular dependencies
- [ ] Output: `KnowledgeObject` with DEPENDS_ON, CALLS relationships
- [ ] Cross-file analysis for multi-module projects

### Day 10 — Code Knowledge Enrichment

- [ ] Map code entities to Jira requirements (regex: `JIRA-123`, `#123` in comments)
- [ ] Map code entities to Confluence docs (links in docstrings, README refs)
- [ ] Tag code with architectural context (module boundaries, package structure)
- [ ] Generate code knowledge embeddings (semantic description of each entity)
- [ ] Cross-link: Code ↔ Requirement ↔ Document
- [ ] Entity enrichment: CLASS, INTERFACE, FUNCTION, METHOD, ENUM, TYPE, VARIABLE

### Day 11 — Code Engine Tests & Integration

- [ ] Test parser on sample Python/TypeScript/Java projects
- [ ] Validate call graph accuracy against known patterns
- [ ] Verify cross-linking with Jira/Confluence references
- [ ] Benchmark: parsing speed for 10k+ line projects (< 1 min for typical project)
- [ ] Integrate with Ingestion Engine pipeline

**Deliverable:** Engine 2 fully functional, AST-based code understanding, dependency/call graphs, cross-linking

---

## Phase 3 — Knowledge Extraction Engine (Day 12–15)

### Goal

Build Engine 3: Convert raw ingested data into explicit, structured knowledge with entities, relationships, decisions, rules. Implements 3-pass hybrid pipeline.

### Day 12 — Entity & Relationship Extraction (Rule-Based)

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

### Day 13 — LLM-Powered Extraction (Model-Agnostic)

- [ ] Define `ExtractionPromptTemplate` — language-agnostic prompts with Jinja2
- [ ] Implement `LLMExtractionAdapter` interface with pluggable implementations
- [ ] Implement `OpenAIAdapter` as default; easily swappable to Claude/Gemini/local
- [ ] Implement `MockAdapter` for testing
- [ ] LLM prompts for: entity identification, relationship inference, decision detection
- [ ] Structured output parsing with JSON mode / regex fallback

### Day 14 — Decision & Rule Detection

- [ ] Implement `ADRDetector` — pattern matching for Architecture Decision Records:
  - Pattern: `ADR-*`, `Decision Record`, `Context/Decision/Consequences` structure
- [ ] Implement `BusinessRuleDetector` — detect "must", "should", "cannot", "required" patterns
- [ ] Implement `ConstraintDetector` — technical constraints, NFRs, security requirements
- [ ] Output: KnowledgeObjects with object_type=DECISION or RULE

### Day 15 — Extraction Pipeline & Validation

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

## Phase 4 — Knowledge Storage Engine (Day 16–19)

### Goal

Build Engine 4: Persistent storage across Vector, Graph, and Metadata layers with full traceability. Implements 4-layer architecture per `core/3-knowledge-model.md`.

### Day 16 — Metadata Store (SQLAlchemy + SQLite)

- [ ] Define DB schema (SQLite for dev, PostgreSQL for prod):
  - `knowledge_objects` — id, object_type, title, description, content, source_references (JSON), confidence, lifecycle_state, created_at, updated_at, tags (JSON), properties (JSON)
  - `sources` — source_id, source_type, url, title, last_synced, content_hash
  - `knowledge_sources` — junction table linking knowledge_objects to sources
  - `relationships` — from_id, to_id, relationship_type, confidence
  - `lifecycle_events` — knowledge_id, from_state, to_state, triggered_at, trigger_reason
- [ ] Implement `MetadataStore` — CRUD with full traceability queries
- [ ] Lifecycle state filtering (exclude DEPRECATED, ARCHIVED from active queries)
- [ ] Source reference integrity checks

### Day 17 — Vector Store (ChromaDB)

- [ ] Implement `VectorStore` interface (provider-agnostic):
  - `upsert(knowledge_chunks: list[KnowledgeChunk]) -> None`
  - `query(query_embedding, top_k, filters) -> list[ScoredChunk]`
  - `delete(ids: list[str]) -> None`
  - `exists(id: str) -> bool`
- [ ] Implement `ChromaDBBackend` as default
- [ ] Implement `EmbeddingGenerator` with OpenAI adapter
- [ ] Chunk knowledge by entity type (512 tokens per chunk, 64 token overlap)
- [ ] Store knowledge + metadata as vectors with filterable attributes (entity_type, lifecycle_state, source_type)

### Day 18 — Graph Store (NetworkX)

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

### Day 19 — Storage Integration & Queries

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

## Phase 5 — Retrieval Intelligence Engine (Day 20–23)

### Goal

Build Engine 5: Intelligent query processing — intent detection, hybrid retrieval, graph traversal, reranking with RRF fusion.

### Day 20 — Intent Detection & Query Planning

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

### Day 21 — Hybrid Retrieval

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

### Day 22 — Graph Traversal & Reranking

- [ ] Implement `GraphTraverser` — BFS/DFS with configurable depth limit (default 3 hops)
- [ ] Implement `Reranker` — weighted scoring:
  - confidence_weight: 0.3
  - lifecycle_weight: 0.2 (ACTIVE > UPDATED > others)
  - recency_weight: 0.1 (prefer recently updated)
  - relevance_weight: 0.4 (query relevance score)
- [ ] Implement `Deduplicator` — merge overlapping results, keep highest confidence
- [ ] Lifecycle filtering: exclude SUPERSEDED, DEPRECATED, ARCHIVED by default

### Day 23 — Retrieval Pipeline & Tests

- [ ] Complete pipeline: Query → Intent → Plan → Hybrid Retrieve → Traverse → Rerank → Results
- [ ] Retrieval metrics implementation:
  - precision@k, recall@k, NDCG
- [ ] Benchmark: < 500ms for 10K knowledge objects
- [ ] Write tests with golden queries and expected results
- [ ] Implement fallback strategies (vector-only if graph unavailable)

**Deliverable:** Engine 5 fully functional, hybrid retrieval with intent detection and RRF fusion, < 500ms latency

---

## Phase 6 — Context Delivery Engine (Day 24–26)

### Goal

Build Engine 6: Assemble retrieval results into model-ready context packages with universal contract. Every output follows `ContextPackage` schema.

### Day 24 — Context Assembly

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

### Day 25 — Model Adapters (Model Independence)

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

### Day 26 — Context Contract & Streaming

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

## Phase 7 — CLI, API & Integration (Day 27–29)

### Goal

Wrap all engines into a usable CLI and REST API. Connect everything into a coherent system with governance enforcement.

### Day 27 — CLI Interface

- [ ] `pkh init` — scaffold project config with all sections
- [ ] `pkh ingest` — full ingestion pipeline with progress tracking
- [ ] `pkh query "question"` — natural language query with intent display
- [ ] `pkh context --query "..."` — raw context package for AI agents
- [ ] `pkh graph --entity "Name"` — visualize knowledge graph (ASCII/JSON)
- [ ] `pkh sync` — incremental sync with change report
- [ ] `pkh status` — ingestion status, counts, freshness, governance violations
- [ ] `pkh audit` — view audit log (ADMIN/ARCHITECT role required)

### Day 28 — REST API

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

### Day 29 — End-to-End Integration

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

## Phase 8 — Evaluation, Docs & Polish (Day 30)

### Goal

Validate quality per `core/8-evaluation-framework.md`, write documentation, prepare for production use.

### Day 30

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

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.10+ | Rich ecosystem for NLP, AST, LLM |
| Knowledge Model | Pydantic v2 | Strong typing, validation, serialization |
| Vector Store | ChromaDB | Lightweight, embedded, no external dep |
| Graph Store | NetworkX | Pure Python, in-memory, serializable |
| Metadata Store | SQLite + SQLAlchemy | Zero config, ACID, portable |
| Code Parsing | tree-sitter | Language-agnostic, incremental, fast |
| LLM Adapters | Strategy pattern + config | True model independence |
| CLI | Typer + Rich | Type-safe CLI, beautiful output |
| API | FastAPI | Async, auto-docs, fast |
| Fusion | Reciprocal Rank Fusion (RRF) | Proven hybrid ranking method |
| Auth | RBAC with JWT/OAuth2 | Granular access control |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM API costs | Rule-based extraction primary, LLM as enrichment only |
| Source API rate limits | Caching, incremental sync, retry with exponential backoff |
| Knowledge drift | Lifecycle state machine, staleness detection (>7d warning, >30d prompt) |
| Context overflow | Smart compression, priority-based truncation, 5 tiers |
| Model lock-in | Adapter pattern, all calls through interfaces |
| Large codebase parsing | Chunked parsing, incremental AST updates, skip test files |
| Stale knowledge | Automatic staleness detection, lifecycle enforcement |
| Security exposure | RBAC enforcement, source-level permission inheritance |

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

