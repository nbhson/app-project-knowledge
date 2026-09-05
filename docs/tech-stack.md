# Technology Stack

> Detailed breakdown of the technologies used in Project Knowledge Harness (PKH), including version information, rationale, and integration points.

[[glossary]]

---

## Overview

PKH employs a carefully selected technology stack designed to balance development productivity, production robustness, and technological flexibility. The stack is organized around six core execution engines and supports multiple deployment environments from local development to enterprise production.

## Core Technologies by Category

### Language & Runtime

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Python** | 3.10+ | Core language, all engines | Rich ecosystem for NLP, AST processing, LLM integration; excellent tooling and community support |
| **PyPy** | Optional | Performance-critical components | ~2-3x speedup for pure Python workloads; compatible with most dependencies |

### Data Modeling & Validation

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Pydantic** | v2.x | Data validation, settings management, API schemas | Runtime validation, serialization, IDE support, excellent performance; v2 offers significant speed improvements |
| **Dataclasses** | Built-in | Internal data structures | Lightweight, minimal overhead for simple data containers |

### Code Analysis & Parsing

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **tree-sitter** | Latest | Language-agnostic parsing | Incremental parsing, robust error recovery, supports 50+ languages, WebAssembly bindings available |
| **Python AST** | Built-in | Python-specific analysis | Deep integration with Python runtime, access to bytecode and runtime information |

### Storage Systems

| Technology | Dev Environment | Prod Environment | Purpose | Rationale |
|------------|-----------------|------------------|---------|-----------|
| **Vector Store** | ChromaDB | pgvector (PostgreSQL extension) | Semantic similarity search | ChromaDB: zero-config dev, embedded; pgvector: production scalability, ACID compliance, SQL integration |
| **Graph Store** | NetworkX | Neo4j | Relationship traversal, pathfinding | NetworkX: pure Python, serializable, dev-friendly; Neo4j: ACID transactions, clustering, advanced graph algorithms |
| **Metadata Store** | SQLite + SQLAlchemy | PostgreSQL | Structured querying, filtering, transactions | SQLite: zero-admin dev; PostgreSQL: enterprise reliability, JSONB, full SQL support |
| **Raw Source Store** | Local Filesystem | S3 / MinIO | Original data preservation, audit trail | Filesystem: simple dev access; S3: durable, scalable, cost-effective blob storage |

### LLM Integration

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Strategy Pattern** | Custom | Model abstraction layer | Enables switching LLMs without code changes; clean separation of concerns |
| **LiteLLM** | Optional | Unified LLM API | Single interface for 100+ LLM providers; includes fallback, load balancing, cost tracking |
| **Prompt Caching** | Custom | Context package compression | Reduces token usage and costs; maintains knowledge fidelity |

### API & Services

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **FastAPI** | Latest | HTTP API server | Async performance, automatic OpenAPI docs, dependency injection, Pydantic integration |
| **Uvicorn** | Latest | ASGI server | High-performance, compatible with FastAPI, HTTP/WebSocket support |
| **Typer** | Latest | CLI framework | Built on Click, automatic help generation, type hints, rich output |
| **Rich** | Latest | CLI formatting | Beautiful terminal output, tables, syntax highlighting, progress bars |
| **Pydantic Settings** | v2.x | Configuration management | Environment variable parsing, secrets management, validation |

### Testing & Quality

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **pytest** | Latest | Testing framework | Fixture-based, excellent plugin ecosystem, async support |
| **pytest-asyncio** | Latest | Async test support | Native async/await testing in pytest |
| **Hypothesis** | Optional | Property-based testing | Finds edge cases through generated test cases |
| **ruff** | Latest | Linting/formatting | Extremely fast Python linter and formatter, replaces flake8+black+isort |
| **mypy** | Latest | Static type checking | Gradual typing, excellent IDE integration, strict mode available |

### Development Tooling

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Poetry** | Latest | Dependency management | Lock files, virtual environments, publishing, replaces pip+venv+pip-tools |
| **pre-commit** | Latest | Git hooks | Automated code quality checks before commit |
| **docker** | Latest | Containerization | Consistent development environments, production deployment |
| **docker-compose** | Latest | Multi-container dev | Orchestrates dev databases, caches, services |
| **just** | Optional | Command runner | Cross-platform make alternative with friendly syntax |

## Development Stack

For local development, PKH uses a lightweight, zero-configuration stack:

```
Development Stack:
├── Language: Python 3.10+
├── Dependency Management: Poetry (or pip)
├── Vector Store: ChromaDB (embedded)
├── Graph Store: NetworkX (pure Python)
├── Metadata Store: SQLite (file-based)
├── Raw Store: Local filesystem
├── Testing: pytest + pytest-asyncio
├── Linting/Formatting: ruff
├── Type Checking: mypy
└── API Docs: Automatic (Swagger UI via FastAPI)
```

To start development:
```bash
python -m venv venv
source venv/bin/activate
poetry install  # or: pip install -e ".[dev]"
pkh init
```

## Production Stack

Production deployments use enterprise-grade, scalable technologies:

```
Production Stack:
├── Language: Python 3.10+ runtime
├── Dependency Management: Poetry/pi wheels
├── Vector Store: pgvector on PostgreSQL 16+
├── Graph Store: Neo4j 5+ (clustered)
├── Metadata Store: PostgreSQL 16+ (with connection pooling)
├── Raw Store: Amazon S3 / GCS / MinIO
├── Caching: Redis 7+ (optional, for query caching)
├── API: FastAPI behind load balancer (NGINX/HAProxy/Cloud LB)
├── Observability: Structured JSON logging, Prometheus metrics
├── Security: TLS termination, OAuth2/JWT, RBAC enforcement
└── Infrastructure: Docker/Kubernetes or VM-based
```

Production deployment example:
```bash
# Using Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Using Kubernetes
kubectl apply -f k8s/
```

## Technology Rationale

### Why Python 3.10+?

1. **Ecosystem**: Best-in-class libraries for NLP (spaCy, transformers), AST processing, and LLM integration
2. **Performance**: Significant improvements over 3.8/3.9, especially in asyncio
3. **Features**: Structural pattern matching, improved error messages, better typing
4. **Support**: Active maintenance, security updates, wide hosting support

### Why This Storage Approach?

PKH uses a **polyglot persistence** strategy, matching each storage technology to its strongest use case:

- **Vector Store (ChromaDB/pgvector)**: Optimized for similarity search - the core retrieval operation
- **Graph Store (NetworkX/Neo4j)**: Optimized for relationship traversal - essential for impact analysis and dependency tracking
- **Metadata Store (SQLite/PostgreSQL)**: Optimized for structured queries and transactions - perfect for lifecycle management and source traceability
- **Raw Store (FS/S3)**: Optimized for blob storage - ideal for preserving original source documents with perfect fidelity

This approach provides:
- **Performance**: Each engine uses the optimal storage technology for its access patterns
- **Scalability**: Each layer can be scaled independently based on workload
- **Flexibility**: Easy to swap implementations as needs evolve
- **Reliability**: Uses battle-tested technologies for each use case

### Why Pydantic v2?

1. **Performance**: ~2-5x faster than v1 for validation and serialization
2. **Features**: Improved JSON schema generation, better validation errors
3. **Maintenance**: Actively developed with strong community backing
4. **Integration**: Native support with FastAPI, SQLModel, and other modern Python tools

### Why tree-sitter for Code Analysis?

1. **Language Agnostic**: Supports 50+ programming languages with consistent APIs
2. **Incremental Parsing**: Reparses only changed parts of files - crucial for performance
3. **Error Tolerance**: Produces useful ASTs even with syntax errors
4. **WebAssembly Support**: Can run in browsers for potential future web-based tools
5. **Active Maintenance**: Backed by GitHub, used in VS Code, Atom, and many other editors

## Integration Points

### Engine-to-Engine Communication

Engines communicate through well-defined interfaces using Pydantic models:

```
Engine 1 (Ingestion) → Engine 2 (Code Intelligence)
    NormalizedRawItem (Pydantic model) → 

Engine 2 → Engine 3 (Knowledge Extraction)
    CodeEntities + CodeRelationships → KnowledgeObjects

Engine 3 → Engine 4 (Knowledge Storage)
    KnowledgeObjects → Persisted across 4 storage layers

Engine 4 ↔ Engine 5 (Retrieval Intelligence)
    Storage queries ←→ RelevantKnowledgeSet

Engine 5 → Engine 6 (Context Delivery)
    RelevantKnowledgeSet → ContextPackage (model-agnostic)
```

### External Integration Points

1. **Source Connectors**: Pluggable interfaces for Git, Confluence, Jira, Documents, API Specs
2. **LLM Adapters**: Strategy pattern allowing any LLM provider (Anthropic, OpenAI, local, etc.)
3. **API Consumers**: REST endpoints for CLI, IDE extensions, web dashboard, custom applications
4. **Authentication**: OAuth2/API Key middleware for secure access
5. **Observability**: Structured logging, metrics endpoints, health checks

## Version Compatibility Matrix

| Component | Minimum Version | Tested Versions | Notes |
|-----------|-----------------|-----------------|-------|
| Python | 3.10 | 3.10, 3.11, 3.12 | 3.9 may work but not officially supported |
| Pydantic | v2.0 | v2.4, v2.5 | v1.x not compatible |
| FastAPI | 0.95.0 | 0.95.x, 0.10x | Requires Pydantic v2 |
| PostgreSQL | 14 | 14, 15, 16 | pgvector requires 14+ |
| Neo4j | 4.4 | 4.4, 5.x | 5.x recommended for performance |
| ChromaDB | 0.4.0 | 0.4.x, 0.5.x | Embedded mode only in dev |
| Redis | 6.0 | 6.x, 7.x | Optional for caching |

## Future Technology Considerations

### Under Evaluation

| Technology | Potential Use | Status |
|------------|---------------|--------|
| **Apache Arrow/Parquet** | Efficient columnar storage for large knowledge sets | Investigation |
| **Milvus/Qdrant** | Specialized vector databases for massive scale | Evaluation |
| **Amazon Neptune** | Managed graph database alternative to Neo4j | Research |
| **Weaviate** | Hybrid vector+graph storage | Proof of concept |
| **mlflow** | LLM experiment tracking and model management | Planned |
| **OpenTelemetry** | Distributed tracing and metrics | Planned |

### LLM Cost Control

- **Default is rule-based** (`llm_enabled=false`). LLM chỉ bật khi rule không đủ — xem `docs/engines/knowledge-extraction-engine.md#cost-control`.
- **Adapter + Mock first:** Mọi test dùng `MockAdapter`; không test nào gọi API thật trong CI.
- **Budget guard & caching:** Batch 10-20 items/prompt, cache `hash(content)`, hard budget `50k tokens/run`.

### Technology Avoidance

PKH intentionally avoids certain technologies to maintain simplicity and focus:

- **Complex Enterprise Service Buses**: Prefer direct API calls or lightweight messaging
- **Heavyweight ORMs**: Use SQLAlchemy Core or raw SQL for performance-critical paths
- **Proprietary Cloud Services**: Design for portability across clouds and on-premises
- **Monolithic Frameworks**: Prefer composable, lightweight libraries
- **LLM-for-everything**: Không dùng LLM cho việc rule-based làm được (AST parsing, Jira field mapping)

## Getting Started with the Technology Stack

### For Developers

1. **Prerequisites**: Python 3.10+, Git
2. **Setup**:
   ```bash
   # Clone and enter directory
   git clone <repository-url>
   cd project-knowledge-harness
   
   # Setup development environment
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   
   # Initialize and run
   pkh init
   pkh ingest --source git://<your-repo>
   ```

### For Production Deployment

1. **Infrastructure**: Provision PostgreSQL, Neo4j, and object storage
2. **Configuration**: Create `settings.prod.yaml` with production connection strings
3. **Deployment**: Use Docker Compose or Kubernetes manifests
4. **Scaling**: Adjust replica counts based on query load
5. **Monitoring**: Set up alerts for query latency, error rates, and storage growth

## Support and Maintenance

### Long-Term Support Commitments

| Technology | LTS Version | Support Until | Notes |
|------------|-------------|---------------|-------|
| Python 3.10 | 3.10.x | 2026-10 | Security updates until EOL |
| PostgreSQL 14 | 14.x | 2026-11 | Extended available via vendors |
| Neo4j 5.x | 5.x | 2027-06 | Neo4j provides LTS releases |
| FastAPI | Latest | N/A | Semantic versioning, breaking changes minor |
| Pydantic | v2.x | N/A | Backward compatibility within major versions |

### Dependency Management

- **Security Updates**: Monitored via GitHub Dependabot and pip-audit
- **Breaking Changes**: Handled through semantic versioning and comprehensive test suite
- **Deprecation Policy**: 1-year deprecation notice for major technology changes
- **Backward Compatibility**: Maintained within major versions where possible

---

> This document represents the current technology stack as of September 2026. For the most up-to-date information, consult the `pyproject.toml`, `requirements.txt`, and deployment guides.