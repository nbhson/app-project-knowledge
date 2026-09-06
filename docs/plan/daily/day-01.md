# Day 1 — Project Scaffolding (Phase 0)

> **Phase:** 0 — Foundation | **Date:** Day 1 of 45 | **Goal:** Set up project structure, core types, and testing framework

---

## 🎯 Daily Target

**Deliverable:** Complete Python project scaffold with:
- `pyproject.toml` with all dependencies
- Package structure `src/pkh/` with all submodules
- Core Pydantic models (enums) defined
- Testing framework (pytest) configured
- Logging infrastructure with JSON output

---

## ✅ Tasks

### 1. Initialize Python Project
- [ ] Create `pyproject.toml` with:
  - Project metadata (name, version, description, authors)
  - Dependencies: `pydantic>=2.0`, `pyyaml`, `sqlalchemy`, `chromadb`, `networkx`, `tree-sitter`, `tree-sitter-python`, `tree-sitter-typescript`, `tree-sitter-java`, `tree-sitter-go`, `tree-sitter-rust`, `tree-sitter-cpp`, `typer`, `rich`, `fastapi`, `uvicorn`, `python-jose`, `passlib`, `tiktoken`, `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`
  - Dev dependencies: `ruff`, `mypy`, `pre-commit`
  - Build system: `setuptools` or `hatch`
- [ ] Create `requirements.txt` (pinned versions from lockfile)
- [ ] Create `.gitignore` for Python (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `*.egg-info`, `.coverage`, `dist/`, `build/`)
- [ ] Create `.env.example` template

### 2. Create Package Structure
```
src/pkh/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   ├── knowledge.py
│   └── lifecycle.py
├── engines/
│   ├── __init__.py
│   ├── ingestion/
│   ├── code_intelligence/
│   ├── extraction/
│   ├── storage/
│   ├── retrieval/
│   └── context_delivery/
├── storage/
│   ├── __init__.py
│   ├── metadata.py
│   ├── vector.py
│   ├── graph.py
│   └── unified.py
├── adapters/
│   ├── __init__.py
│   └── llm.py
├── utils/
│   ├── __init__.py
│   ├── logging.py
│   └── exceptions.py
├── cli/
│   ├── __init__.py
│   └── main.py
├── api/
│   ├── __init__.py
│   ├── main.py
│   └── auth.py
└── governance/
    ├── __init__.py
    └── audit.py
```

### 3. Define Core Enums (in `models/knowledge.py`)
- [ ] `LifecycleState` enum: `DISCOVERED`, `EXTRACTED`, `VALIDATING`, `ACTIVE`, `UPDATED`, `SUPERSEDED`, `DEPRECATED`, `ARCHIVED`
- [ ] `ObjectType` enum: `ENTITY`, `RELATIONSHIP`, `DECISION`, `RULE`
- [ ] `EntityType` enum (23 types — canonical):
  - Code (11): `REPOSITORY`, `MODULE`, `PACKAGE`, `FILE`, `CLASS`, `INTERFACE`, `FUNCTION`, `METHOD`, `ENUM`, `TYPE`, `VARIABLE`
  - Project (4): `EPIC`, `STORY`, `TASK`, `BUG`
  - Document (4): `DOCUMENT`, `REQUIREMENT`, `DECISION`, `BUSINESS_RULE` (legacy alias `ADR→DECISION`)
  - System (4): `API`, `DATABASE`, `SERVICE`, `ENDPOINT` (legacy aliases `API_SPEC→API`, `COMPONENT/INFRASTRUCTURE→SERVICE` via `_missing_`)
- [ ] `RelationshipType` enum (15 types):
  - `IMPLEMENTS`, `DEPENDS_ON`, `CALLS`, `USES`, `OWNS`, `DOCUMENTS`, `REQUIRES`, `SUPERSEDES`, `RELATED_TO`, `AFFECTS`, `PART_OF`, `TRACES_TO`, `CONTAINS`, `EXTENDS`, `IMPLEMENTS_IFACE`
- [ ] `SourceType` enum: `GIT`, `CONFLUENCE`, `JIRA`, `DOCUMENT`, `API_SPEC`

### 4. Define SourceReference Model (in `models/knowledge.py`)
- [ ] `SourceReference` Pydantic model:
  - `source_type: SourceType`
  - `source_id: str`
  - `url: str | None`
  - `title: str | None`
  - `last_synced: datetime`
  - `extra: dict[str, Any]` (type-specific keys)

### 5. Setup Testing Framework
- [ ] Create `tests/` directory with `__init__.py`
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Create `tests/unit/`, `tests/integration/` directories
- [ ] Configure `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]`
- [ ] Add test command to `pyproject.toml` scripts

### 6. Setup Logging Infrastructure (in `utils/logging.py`)
- [ ] Structured JSON logging with `structlog` or stdlib `logging` + `python-json-logger`
- [ ] Correlation ID support for request tracing
- [ ] Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- [ ] Output to stdout (container-friendly) and optional file rotation

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `pip install -e .` installs package successfully | ☐ |
| `pytest tests/` runs without errors (0 tests pass) | ☐ |
| All enums importable: `from pkh.models.knowledge import LifecycleState, EntityType, ...` | ☐ |
| `SourceReference` model validates required fields | ☐ |
| JSON logging outputs to stdout | ☐ |
| Package structure matches spec exactly | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 2 (KnowledgeObject model needs enums)
- **Blocked by:** None (starting day)

---

## 📝 Notes

- Use `pydantic-settings` for config management
- Keep `pyproject.toml` as single source of truth for dependencies
- Run `pre-commit install` after creating config
- Commit: `feat: project scaffold with core enums and package structure`