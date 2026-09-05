# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project Knowledge Harness (PKH)** — A continuously evolving, connected, model-independent knowledge system for software projects. Transforms fragmented project information (Git, Confluence, Jira, Documents) into structured, traceable knowledge with full lifecycle management.

> ⚠️ **Design-spec only — no `src/` yet.** All `pkh ingest/query` commands in docs are specs for Phase 0–7. Do not claim a phase is done without `pytest` logs. See `docs/plan/plan.md#current-status` and `docs/decisions/`.

## Key Commands

```bash
# Install dependencies (includes dev tools)
pip install -e ".[dev]"

# Run tests
pytest tests/                    # All tests
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests only
pytest tests/ -k "test_name"     # Single test
pytest tests/ -v --cov=src/pkh   # With coverage

# Lint & Type check
ruff check src/ tests/
ruff format src/ tests/
mypy src/

# Run CLI
pkh init                          # Scaffold config
pkh ingest --source git://...     # Ingest from source
pkh query "How does X work?"      # Natural language query
pkh context --query "..."         # Get context package
pkh graph --entity "Name"         # Visualize knowledge graph
pkh status                        # Check status
pkh audit                         # View audit log

# Run API server
uvicorn src.pkh.api.main:app --reload

# Generate daily plan files (for development planning)
# See docs/plan/daily/ for 45-day implementation plan (was 30)
```

## Architecture

### 6-Engine Pipeline

```
DATA SOURCES (Git, Confluence, Jira, Documents)
         │
         ▼
① INGESTION ENGINE ──► Connect, sync, normalize raw data
         │
         ▼
② CODE INTELLIGENCE ──► tree-sitter AST parsing, symbols, call graphs
         │
         ▼
③ KNOWLEDGE EXTRACTION ──► Rule-based + LLM entity/relationship extraction
         │
         ▼
④ KNOWLEDGE STORAGE ──► Vector (ChromaDB) + Graph (NetworkX) + Metadata (SQLite)
         │
         ▼
⑤ RETRIEVAL INTELLIGENCE ──► Intent classification, hybrid search (RRF), reranking
         │
         ▼
⑥ CONTEXT DELIVERY ──► ContextPackage, 5-tier compression, model adapters
         │
         ▼
CONSUMERS (CLI, REST API, IDE, Agent SDK)
```

### Core Data Models

**KnowledgeObject** — The fundamental unit with:
- `id` (UUID), `object_type` (ENTITY/RELATIONSHIP/DECISION/RULE)
- `title`, `description`, `content`
- `source_references` (required, non-empty) — **Source traceability is mandatory**
- `confidence` (0.0-1.0) — **Always attached**
- `lifecycle_state` — 8 states with strict transition rules

**Lifecycle States** (valid transitions only):
```
DISCOVERED → EXTRACTED → VALIDATING → ACTIVE ←→ UPDATED
                                    ↓
                              SUPERSEDED → DEPRECATED → ARCHIVED
```

**SourceReference** — Links back to source (GIT, CONFLUENCE, JIRA, DOCUMENT, API_SPEC)

## Project Structure

```
src/pkh/
├── config/           # Pydantic Settings (YAML + env vars)
├── models/           # KnowledgeObject, SourceReference, Enums
├── engines/
│   ├── ingestion/    # Connectors (Git, Confluence, Jira, Doc), SyncManager
│   ├── code_intelligence/  # tree-sitter parsers, analyzers
│   ├── extraction/   # Entity/relationship extractors, pipeline
│   ├── retrieval/    # Intent classifier, hybrid retriever, reranker
│   └── context_delivery/   # ContextPackage, assembler, adapters
├── storage/
│   ├── metadata.py   # SQLAlchemy (SQLite/PostgreSQL)
│   ├── vector.py     # ChromaDB/pgvector
│   ├── graph.py      # NetworkX/Neo4j
│   └── unified.py    # KnowledgeStore unified interface
├── adapters/         # LLM adapters (Claude, GPT, Gemini, Local, Mock)
├── utils/            # Logging, exceptions
├── cli/              # Typer CLI commands
├── api/              # FastAPI app + RBAC auth
└── governance/       # Audit logging
```

## Important Files to Know

| File | Purpose |
|------|---------|
| `docs/plan/plan.md` | Master 45-day implementation plan |
| `docs/plan/daily/` | Day-by-day targets (45 files) |
| `config/settings.yaml.example` | Full configuration template |
| `src/pkh/models/knowledge.py` | Core Pydantic models |
| `src/pkh/models/lifecycle.py` | State machine with transition validation |

## Configuration

Edit `config/settings.yaml` (copy from `config/settings.yaml.example`):
- **Sources**: Git, Confluence, Jira, Documents with auth/sync intervals
- **Storage**: Vector (chroma/pgvector), Graph (networkx/neo4j), Metadata (sqlite/postgresql)
- **Retrieval**: RRF fusion (k=60), strategy weights per intent type
- **Adapters**: Default model (claude/openai/gemini/local) with API keys from env
- **Governance**: RBAC roles, audit retention

## Design Principles (Non-Negotiable)

1. **Knowledge First** — Model is replaceable, knowledge is permanent
2. **Source Traceability** — Every KnowledgeObject requires non-empty `source_references`
3. **Confidence Always** — All extracted knowledge has `confidence: 0.0-1.0`
4. **Model Independence** — Swap LLM via config only (adapter pattern)

## Testing

```bash
# Unit tests: fast, mock external services
pytest tests/unit/ -v

# Integration tests: require config, test full pipeline
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_models.py -v

# With coverage
pytest tests/ --cov=src/pkh --cov-report=term-missing
```

## Development Notes

- **Python 3.10+**, Pydantic v2, SQLAlchemy 2.0
- **tree-sitter Python-first MVP** — `tree-sitter-python` Day 8, other languages are plugin post-MVP (`docs/decisions/adr-003-code-parsing.md`)
- **Polyglot persistence:** Metadata (SQLite/Postgres) is the source of truth; Vector/Graph/Raw are derived and rebuildable via outbox (`docs/engines/knowledge-storage-engine.md`, `adr-002`)
- **LLM off by default:** `extraction.llm_enabled=false`, batching + cache + budget 50k tokens/run, `MockAdapter` for all tests (`adr-004`)
- **MVP first:** Day 1–7 = Git + Python + rule-only + SQLite/Chroma/NetworkX + vector-only + Mock — do not touch Confluence/Jira/Neo4j/pgvector until MVP passes
- **Async-first:** Use `asyncio` for I/O (connectors, API, LLM calls)
- **Config via Pydantic Settings:** YAML file + `PKH_` env var overrides
- **Structured logging:** JSON output with correlation IDs
- **Error hierarchy:** `PKHError` base with specific subclasses
- **Verification:** Phase done = `pytest` + `ruff` + `mypy` pass — not just docs

## Key Reference Docs

- `docs/core/1-vision-and-design-principles.md` — Vision
- `docs/core/2-architecture.md` — System architecture
- `docs/core/3-knowledge-model.md` — Entity/relationship types
- `docs/core/4-knowledge-lifecycle.md` — State transitions & rules
- `docs/core/5-source-of-truth-model.md` — Source hierarchy
- `docs/core/6-retrieval-strategy.md` — Retrieval strategies per intent
- `docs/core/7-context-contract.md` — ContextPackage schema
- `docs/core/8-evaluation-framework.md` — Quality metrics
- `docs/core/9-governance-and-trust-model.md` — RBAC/audit
- `docs/decisions/` — Architecture Decision Records (ADRs)
- `docs/glossary.md` — Term definitions
