# PKH - Project Knowledge Harness

> Transform fragmented project information into a continuously evolving, connected, model-independent knowledge system.

## Architecture

```mermaid
graph TD
    A[DATA SOURCES\nGit Repo | Confluence | Jira | Documents | API Specs] --> B[① INGESTION ENGINE]

    B --> C{Code or Docs?}
    C -->|Code| D[② CODE INTELLIGENCE ENGINE\ntree-sitter | AST | Symbols | Call graphs]
    C -->|Docs| E[③ KNOWLEDGE EXTRACTION ENGINE\nHybrid: Rule-based + LLM-assisted]

    D --> E
    E --> F[④ KNOWLEDGE STORAGE ENGINE\nVector Store | Graph Store | Metadata Store | Raw Sources]

    F --> G[⑤ RETRIEVAL INTELLIGENCE ENGINE\nIntent → Plan → Hybrid Retrieve → Rerank → Dedup]
    G --> H[⑥ CONTEXT DELIVERY ENGINE\nContextPackage | 5-tier compression | Model adapters]

    H --> I[CONSUMERS\nCLI | REST API | IDE | Agent SDK]
```

## Design Principles

1. **Knowledge First** — Model is replaceable, knowledge is permanent
2. **Source Traceability** — Every knowledge traces back to its source via SourceReference
3. **Never Trust Extracted Knowledge Completely** — Confidence scores always attached (0.0–1.0)
4. **Model Independence** — Any LLM can be swapped without changing knowledge core

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Initialize config
pkh init

# Ingest a project (all sources)
pkh ingest --source git://https://github.com/org/project \
           --source confluence://PROJ-SPACE \
           --source jira://MYPROJECT

# Incremental sync (only changes)
pkh ingest --sync --incremental

# Query knowledge
pkh query "How does payment flow work?"

# Get context for AI agent
pkh context --query "Explain the authentication module"

# View knowledge graph
pkh graph --entity "PaymentService"

# Check status
pkh status
```

## Configuration

Edit `config/settings.yaml`:

```yaml
# ── Sources ──────────────────────────────────────────────────────────
sources:
  git:
    repos:
      - url: https://github.com/org/project
        branch: main
        sync_interval: 5m
        auth:
          type: token
          token_ref: secrets.GIT_TOKEN
        include_paths: ["**/*.py", "**/*.ts", "**/openapi.yaml"]
        exclude_paths: ["**/test_*.py", "**/__pycache__/**"]
  
  confluence:
    base_url: https://your-company.atlassian.net
    spaces: [PROJ, DOCS]
    sync_interval: 1h
    auth:
      type: oauth2
  
  jira:
    base_url: https://your-company.atlassian.net
    projects: [PROJ]
    sync_interval: 15m
    auth:
      type: oauth2
    issue_types: [Bug, Story, Task, Epic]
  
  documents:
    paths:
      - local: ./docs
      - url: https://example.com/specs
    sync_interval: 1h
    supported_formats: [md, pdf, yaml, json]

# ── Storage ──────────────────────────────────────────────────────────
storage:
  vector:
    provider: chroma        # chroma | pgvector
    path: ./data/vectorstore
  graph:
    provider: networkx      # networkx | neo4j
    path: ./data/graph
  metadata:
    provider: sqlite        # sqlite | postgresql
    path: ./data/metadata.db
  raw:
    provider: filesystem    # filesystem | s3
    path: ./data/raw

# ── Retrieval ────────────────────────────────────────────────────────
retrieval:
  top_k: 10
  min_confidence: 0.3
  hybrid: true
  rerank: true
  fusion:
    method: rrf             # rrf | weighted
    k: 60
  strategies:
    vector:
      enabled: true
      top_k: 20
      threshold: 0.75
    keyword:
      enabled: true
      boost_title: 2.0
    graph:
      enabled: true
      max_hops: 3
      relations: [DEPENDS_ON, CALLS, USES, AFFECTS, IMPLEMENTS]
  reranking:
    confidence_weight: 0.3
    lifecycle_weight: 0.2
    recency_weight: 0.1
    relevance_weight: 0.4

# ── LLM Adapters ─────────────────────────────────────────────────────
adapters:
  default: claude
  models:
    claude:
      model: claude-sonnet-4-20250514
      api_key: ${ANTHROPIC_API_KEY}
    openai:
      model: gpt-4o
      api_key: ${OPENAI_API_KEY}

# ── Governance ───────────────────────────────────────────────────────
governance:
  rbac:
    default_role: developer
  audit:
    enabled: true
    retention_years: 1
```

---

## Core Concepts

### KnowledgeObject — The Fundamental Unit

Every piece of knowledge in the system is a `KnowledgeObject`:

```python
class KnowledgeObject(BaseModel):
    id: str                              # UUID v4
    object_type: ObjectType              # ENTITY | RELATIONSHIP | DECISION | RULE
    title: str
    description: str = ""
    content: str = ""                    # For vector indexing
    source_references: list[SourceReference]  # ALWAYS non-empty
    confidence: float = 1.0              # 0.0 - 1.0
    lifecycle_state: LifecycleState      # See lifecycle below
    created_at: datetime
    updated_at: datetime
    tags: list[str] = []
    properties: dict[str, Any] = {}
```

### Knowledge Lifecycle

> Full lifecycle details: `docs/core/4-knowledge-lifecycle.md`

```
DISCOVERED → EXTRACTED → VALIDATING → ACTIVE ←→ UPDATED
                                      ↓
                                SUPERSEDED → DEPRECATED → ARCHIVED
```

| State | Description | Queryable? |
|-------|-------------|------------|
| DISCOVERED | Raw data found, not processed | No |
| EXTRACTED | Knowledge extracted, pending validation | Yes (flagged) |
| VALIDATING | Under validation checks | No |
| ACTIVE | Validated and live | Yes |
| UPDATED | Source changed, re-validation pending | Yes (flagged) |
| SUPERSEDED | Replaced by newer knowledge | No |
| DEPRECATED | No longer in use | No |
| ARCHIVED | Preserved for history (read-only) | No (read-only) |

| DEPRECATED | No longer in use | No |
| ARCHIVED | Preserved for history (read-only) | No (read-only) |

**Staleness rules:** >7 days unsynced → warning; >30 days → prompt re-sync; >90 days → suggest deprecation.

### Source of Truth

| Knowledge | Source of Truth |
|-----------|----------------|
| Code implementation | Git Repository (commit hash) |
| Requirement | Jira (issue key) |
| Architecture decision | Confluence / ADR (page ID) |
| API Contract | OpenAPI spec (file path + endpoint) |
| Deployment | Infrastructure config (versioned) |

Every `KnowledgeObject` carries one or more `SourceReference`s that link back to the original source. This ensures full traceability: **"Where did this come from?"** always has an answer.

### SourceReference

```python
class SourceReference(BaseModel):
    source_type: SourceType              # GIT | CONFLUENCE | JIRA | DOCUMENT | API_SPEC
    source_id: str                       # commit hash, page ID, issue key, etc.
    url: str = ""                        # Direct link to source
    title: str = ""
    last_synced: datetime
    extra: dict[str, Any] = {}           # Type-specific metadata
```

### Entity Types (23 total)

| Category | Types |
|----------|-------|
| **Code** (11) | REPOSITORY, MODULE, PACKAGE, FILE, CLASS, INTERFACE, FUNCTION, METHOD, ENUM, TYPE, VARIABLE |
| **Project** (4) | EPIC, STORY, TASK, BUG |
| **Document** (4) | REQUIREMENT, DECISION, DOCUMENT, BUSINESS_RULE |
| **System** (4) | API, DATABASE, SERVICE, ENDPOINT |

### Relationship Types (15 total)

`IMPLEMENTS` · `DEPENDS_ON` · `CALLS` · `USES` · `OWNS` · `DOCUMENTS` · `REQUIRES` · `SUPERSEDES` · `RELATED_TO` · `AFFECTS` · `PART_OF` · `TRACES_TO` · `CONTAINS` · `EXTENDS` · `IMPLEMENTS_IFACE`

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `pkh init` | Scaffold project config |
| `pkh ingest --source <type>://<path>` | Ingest from a source |
| `pkh ingest --sync [--incremental]` | Run sync pipeline |
| `pkh query "<question>"` | Natural language query |
| `pkh context --query "..."` | Get raw context package for AI agents |
| `pkh graph --entity "Name"` | Visualize knowledge graph |
| `pkh status` | Show ingestion status, counts, freshness |
| `pkh audit` | View audit log (ADMIN/ARCHITECT) |

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Trigger ingestion |
| `/ingest/status` | GET | Check ingestion status |
| `/query` | POST | Natural language query |
| `/context` | POST | Get context package |
| `/knowledge/{id}` | GET | Get knowledge object |
| `/graph/explore` | GET | Explore knowledge graph |
| `/sources/status` | GET | Check source sync status |
| `/health` | GET | Health check |

## Access Control (RBAC)

| Role | Can Read | Can Ingest | Can Configure | Can Audit |
|------|----------|------------|---------------|-----------|
| ADMIN | All | All | All | All |
| ARCHITECT | All | All | No | Yes |
| DEVELOPER | Own projects | Own repos | No | No |
| VIEWER | Public only | No | No | No |
| SERVICE | Scoped | Scoped | No | No |

---

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Language | Python 3.10+ | Rich ecosystem for NLP, AST, LLM |
| Models | Pydantic v2 | Strong typing, validation, serialization |
| Code Parsing | tree-sitter | Language-agnostic, incremental, fast |
| Vector Store | ChromaDB (dev) / pgvector (prod) | Lightweight, embedded |
| Graph Store | NetworkX (dev) / Neo4j (prod) | Pure Python, serializable |
| Metadata Store | SQLite + SQLAlchemy (dev) / PostgreSQL (prod) | Zero config, ACID |
| LLM Adapters | Strategy pattern + config | True model independence |
| CLI | Typer + Rich | Type-safe, beautiful output |
| API | FastAPI | Async, auto-docs, fast |
| Testing | pytest | Industry standard |

---

## Comparison with Alternatives

SO SÁNH VỚI CÁC PHƯƠNG ÁN THAY THẾ

| Tiêu chí | PKH | Công cụ wiki truyền thống (Confluence, Notion) | Công cụ tìm kiếm mã (Sourcegraph, GitHub Code Search) | Hệ thống RAG tổng quát |
|----------|-----|-----------------------------------------------|------------------------------------------------------|----------------------|
| **Cấu trúc kiến trúc** | ✅ Đối tượng có cấu trúc + mối quan hệ | ❌ Văn bản tự do, ít cấu trúc | ❌ Chỉ mã, không có mối quan hệ sémantics | ⚠️ Phụ thuộc vào chunking, thiếu ontology |
| **Nguồn gốc truy vết** | ✅ SourceReference bắt buộc | ❌ Thường thiếu hoặc thủ công | ✅ Liên kết trực tiếp tới mã | ⚠️ Thường thiếu, phụ thuộc vào metadata |
| **Điểm số độ tin cậy** | ✅ 0.0-1.0 cho mọi kiến thức trích xuất | ❌ Không có | ❌ Không áp dụng (mã là nguồn thật) | ⚠️ Có đôi khi nhưng không nhất quán |
| **Chu kỳ đời sống** | ✅ Đầy đủ (7 trạng thái, quy chuyển đổi) | ❌ Tĩnh | ❌ Không áp dụng | ❌ Thường thiếu |
| **Độc lập mô hình** | ✅ ContextPackage + Adapter | ❌ Thường gắn với UI cụ thể | ✅ API độc lập | ⚠️ Thụ động phụ thuộc qua prompt |
| **Phạm vi kiến thức** | ✅ Toàn bộ (mã, dự án, tài liệu, hệ thống) | ❌ Chủ yếu tài liệu | ❌ Chỉ mã | ⚠️ Phụ thuộc vào nguồn dữ liệu đầu vào |
| **Chất lượng đo lường** | ✅ Framework toàn diện | ❌ Hạn chế | ⚠️ Một số metrics | ⚠️ Phụ thuộc vào triển khai cụ thể |

---

## Kết luận

PKH là một trong những thiết kế kiến thức dự án tốt nhất và hoàn chỉnh nhất trong tài liệu. Nó thành công trong việc:

- **Giải quyết vấn đề đúng**: Thông tin dự án phân mảnh là một vấn đề thực tế và đáng kể trong phát triển phần mềm
- **Áp dụng nguyên tắc thiết kế vững vàng**: Knowledge First, Source Traceability, Confidence Scoring, Model Independence
- **Cung cấp giải pháp cụ thể và có thể đo lường**: Các thực thể, mối quan hệ, chu kỳ đời sống, và framework đánh giá rõ ràng
- **Cân bằng giữa lý tưởng và thực tiễn**: Từ ví dụ cụ thể (ADR lifecycle, PaymentService) đến CLI và cấu hình YAML thực tế

---

## Design Principles

1. **Knowledge First** — Model is replaceable, knowledge is permanent
2. **Source Traceability** — Every knowledge answers "where did this come from?"
3. **Never Trust Extracted Knowledge Completely** — Confidence scores always attached
4. **Model Independence** — Any LLM can be swapped without changing knowledge core

