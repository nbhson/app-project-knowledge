# ADR-001: Python 3.10+ + Pydantic v2 + FastAPI/Typer

Date: 2026-09-06
Status: Accepted

## Context

PKH cần: NLP/AST/LLM ecosystem tốt, validation mạnh cho KnowledgeObject, API async với auto docs, CLI type-safe. Cần quyết định ngôn ngữ và framework modeling trước khi code Phase 0.

## Decision

- **Language:** Python 3.10+ (không 3.9, không Node/Go). Lý do: ecosystem tốt nhất cho tree-sitter bindings, LLM SDKs, spaCy/transformers, Pydantic.
- **Modeling:** Pydantic v2 (không dataclass thuần, không attrs). Lý do: 2-5x nhanh hơn v1, JSON schema, tích hợp FastAPI native, validation `source_references` non-empty và `confidence 0.0-1.0` ngay trong model.
- **API:** FastAPI + Uvicorn (không Flask/Django). Lý do: async-first, Pydantic integration, auto OpenAPI.
- **CLI:** Typer + Rich (không Click thuần, không argparse). Lý do: type hints, auto help, rich tables/progress cho `pkh ingest` và `pkh graph`.

## Consequences

- (+) Đồng nhất stack Python cho cả 6 engines.
- (+) Pydantic v2 cho phép `KnowledgeObject` là single source of truth cho cả storage và API.
- (-) Yêu cầu Python 3.10+ (bỏ 3.9).
- (-) Pydantic v1 không tương thích — phải lock v2.4+.

## Alternatives Considered

- TypeScript/Node: tốt cho IDE plugin nhưng kém cho ML/AST.
- Go: hiệu năng tốt nhưng thiếu LLM ecosystem và Pydantic tương đương.
- Dataclass + marshmallow: nhẹ hơn nhưng mất validation mạnh và JSON schema.
