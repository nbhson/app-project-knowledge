# ADR-003: tree-sitter Python-First Incremental Parsing

Date: 2026-09-06
Status: Accepted
Related: docs/engines/code-intelligence-engine.md

## Context

Cần parse code thành entities (CLASS, FUNCTION...) và relationships (DEPENDS_ON, CALLS). Yêu cầu: đa ngôn ngữ, incremental (chỉ parse file đổi), chịu lỗi syntax. Chọn parser nào và hỗ trợ bao nhiêu ngôn ngữ ngay từ MVP?

## Decision

- **Parser:** `tree-sitter` (không Python `ast` thuần, không LSP, không regex-only).
- **MVP:** Chỉ **Python** (`tree-sitter-python`). Các ngôn ngữ khác (TS/JS/Java/Go/Rust/C++) là plugins thêm sau khi Python benchmark đạt `<1min cho 10k lines`.
- **Fallback:** Nếu tree-sitter fail (syntax error), fallback về regex text-based extraction và ghi `confidence=0.5, warnings`.

## Consequences

- (+) Language-agnostic API, incremental parsing, error recovery tốt, 50+ languages có sẵn.
- (+) Thêm ngôn ngữ = thêm 1 adapter trong `parsers/`, không sửa core.
- (-) Tree-sitter binding cho Python đôi khi lag version so với Node.
- (-) Phải maintain `extra` per-language trong SourceReference.

## Alternatives Considered

- **Python `ast` builtin:** chỉ Python, không incremental, không đa ngôn ngữ.
- **LSP (Language Server Protocol):** mạnh nhưng nặng, cần chạy server per-language, overkill cho MVP.
- **Regex-only:** đơn giản nhưng miss inheritance, decorator, call graph cross-file.
- **Hỗ trợ 6 languages ngay MVP:** bị over-engineering — tăng scope 3x, chưa có nhu cầu thực tế.
