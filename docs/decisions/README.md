# Decisions (ADRs)

> Ghi lại các quyết định kiến trúc quan trọng của PKH. Mỗi ADR tuân theo template: Context → Decision → Consequences → Alternatives considered.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](adr-001-language-and-modeling.md) | Python 3.10+ + Pydantic v2 + FastAPI/Typer | Accepted |
| [ADR-002](adr-002-storage.md) | Polyglot persistence với dev/prod split | Accepted |
| [ADR-003](adr-003-code-parsing.md) | tree-sitter Python-first incremental | Accepted |
| [ADR-004](adr-004-llm-adapter.md) | Strategy pattern + MockAdapter, LLM off by default | Accepted |
| [ADR-005](adr-005-retrieval.md) | Hybrid RRF (k=60) + 5-tier compression | Accepted |

Để thêm ADR mới: copy `adr-000-template.md` và điền.
