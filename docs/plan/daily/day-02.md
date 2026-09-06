# Day 2 — Knowledge Model & Config (Phase 0)

> **Phase:** 0 — Foundation | **Date:** Day 2 of 45 | **Goal:** Complete KnowledgeObject model, lifecycle state machine, and YAML config system

---

## 🎯 Daily Target

**Deliverable:** Full typed knowledge model with validation, config system, and unit tests

---

## ✅ Tasks

### 1. Implement KnowledgeObject Model (`models/knowledge.py`)
- [ ] `KnowledgeObject` Pydantic model with fields:
  - `id: UUID4` (auto-generated)
  - `object_type: ObjectType` (required)
  - `entity_type: EntityType | None` (required if ENTITY)
  - `title: str` (required, non-empty, max 500)
  - `description: str | None`
  - `content: str` (required, non-empty)
  - `source_references: list[SourceReference]` (required, min_length=1)
  - `confidence: float` (ge=0.0, le=1.0, default=0.5)
  - `lifecycle_state: LifecycleState` (default=DISCOVERED)
  - `created_at: datetime` (auto)
  - `updated_at: datetime` (auto)
  - `tags: list[str]` (default=[])
  - `properties: dict[str, Any]` (default={})
- [ ] Validators:
  - `source_references` non-empty
  - `confidence` in [0, 1]
  - `entity_type` required when `object_type == ObjectType.ENTITY`
  - `content` non-empty string

### 2. Implement Lifecycle State Machine (`models/lifecycle.py`)
- [ ] `LifecycleStateMachine` class with valid transitions (14 total from `core/4-knowledge-lifecycle.md`):
  - `DISCOVERED → EXTRACTED`
  - `EXTRACTED → VALIDATING`
  - `VALIDATING → ACTIVE` | `VALIDATING → SUPERSEDED`
  - `ACTIVE → UPDATED` | `ACTIVE → SUPERSEDED` | `ACTIVE → DEPRECATED`
  - `UPDATED → ACTIVE` | `UPDATED → SUPERSEDED`
  - `SUPERSEDED → ARCHIVED`
  - `DEPRECATED → ARCHIVED`
  - `ARCHIVED` (terminal)
- [ ] Method `can_transition(from_state, to_state) -> bool`
- [ ] Method `transition(knowledge_obj, new_state, reason) -> KnowledgeObject`
- [ ] Auto-set `updated_at` on transition
- [ ] Record transition in `lifecycle_events` (for audit)

### 3. Implement Config System (`config/settings.py`)
- [ ] `SourceConfig` with nested configs:
  - `git: GitSourceConfig` (repos list, auth, branch patterns)
  - `confluence: ConfluenceSourceConfig` (url, spaces, auth, page patterns)
  - `jira: JiraSourceConfig` (url, projects, auth, issue types)
  - `documents: DocumentSourceConfig` (paths, glob patterns, parsers)
- [ ] `StorageConfig`:
  - `metadata: MetadataStoreConfig` (sqlite_path, pool_size)
  - `vector: VectorStoreConfig` (provider=chroma, path, collection, embedding_model)
  - `graph: GraphStoreConfig` (provider=networkx, persist_path)
- [ ] `RetrievalConfig`:
  - `strategies: list[str]` (vector, keyword, graph)
  - `fusion: FusionConfig` (method=RRF, k=60)
  - `weights_per_intent: dict[str, dict[str, float]]`
  - `reranker: RerankerConfig` (weights for confidence, lifecycle, recency, relevance)
- [ ] `AdapterConfig`:
  - `default: str` (openai, claude, gemini, local)
  - `openai: OpenAIAdapterConfig` (model, api_key_env, max_tokens)
  - `claude: ClaudeAdapterConfig` (model, api_key_env)
  - `gemini: GeminiAdapterConfig` (model, api_key_env)
  - `local: LocalAdapterConfig` (model_path, context_window)
- [ ] `GovernanceConfig`:
  - `rbac_enabled: bool`
  - `roles: list[RoleConfig]` (name, permissions)
  - `audit_retention_days: int`
- [ ] `Settings` root model with `model_config = SettingsConfigDict(yaml_file="config.yaml", env_prefix="PKH_")`
- [ ] `get_settings()` singleton function with caching

### 4. Create Example Config (`config.yaml.example`)
```yaml
sources:
  git:
    repos:
      - url: "git@github.com:org/repo.git"
        branch: "main"
        auth: "ssh"
  confluence:
    url: "https://company.atlassian.net/wiki"
    spaces: ["ENG", "ARCH"]
  jira:
    url: "https://company.atlassian.net"
    projects: ["PROJ"]
  documents:
    paths: ["./docs", "./specs"]
    patterns: ["*.md", "*.pdf", "*.yaml"]

storage:
  metadata:
    sqlite_path: "./data/pkh.db"
  vector:
    provider: "chroma"
    path: "./data/chroma"
    collection: "knowledge"
    embedding_model: "text-embedding-3-small"
  graph:
    provider: "networkx"
    persist_path: "./data/graph.json"

retrieval:
  strategies: ["vector", "keyword", "graph"]
  fusion:
    method: "rrf"
    k: 60

adapters:
  default: "openai"
  openai:
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"

governance:
  rbac_enabled: true
```

### 5. Write Unit Tests (`tests/unit/test_models.py`, `tests/unit/test_config.py`)
- [ ] Test `KnowledgeObject` validation (valid/invalid inputs)
- [ ] Test `SourceReference` validation
- [ ] Test lifecycle transitions (valid/invalid)
- [ ] Test config loading from YAML + env vars
- [ ] Test config validation errors

### 6. Error Handling Infrastructure (`utils/exceptions.py`)
- [ ] Exception hierarchy:
  - `PKHError` (base)
  - `ValidationError` (model validation failures)
  - `ConfigurationError` (config loading/validation)
  - `SourceError` (connector failures)
  - `StorageError` (DB/vector/graph failures)
  - `ExtractionError` (extraction pipeline failures)
  - `RetrievalError` (query/retrieval failures)
  - `AdapterError` (LLM adapter failures)
  - `GovernanceError` (RBAC/audit violations)

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `KnowledgeObject` creates with all required fields | ☐ |
| `KnowledgeObject` rejects empty `source_references` | ☐ |
| `KnowledgeObject` rejects `confidence` outside [0,1] | ☐ |
| Lifecycle transitions enforce valid paths only | ☐ |
| Invalid transition raises `ValidationError` | ☐ |
| Config loads from `config.yaml` + env overrides | ☐ |
| All nested configs validate correctly | ☐ |
| Unit tests pass: `pytest tests/unit/test_models.py tests/unit/test_config.py -v` | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 3 (Ingestion connectors need KnowledgeObject, SourceReference, Config)
- **Blocked by:** Day 1 (enums, package structure)

---

## 📝 Notes

- Use `pydantic.Field()` for validation constraints
- `model_config = ConfigDict(validate_assignment=True, extra="forbid")` on all models
- Transition reason should be stored for audit trail
- Config example file should be committed, actual config gitignored
- Commit: `feat: knowledge model, lifecycle state machine, config system`