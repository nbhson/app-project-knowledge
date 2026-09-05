# ADR-004: LLM Adapter (Strategy) + Mock-First + LLM Off By Default

Date: 2026-09-06
Status: Accepted
Related: docs/engines/knowledge-extraction-engine.md, docs/engines/context-delivery-engine.md

## Context

PKH tuyên bố "Model Independence" — phải swap LLM bằng config, không đổi code. Đồng thời LLM API tốn tiền và confidence do LLM gán thường over-confident.

## Decision

- **Pattern:** Strategy `ModelAdapter` protocol (`adapt`, `parse_response`, `get_token_limit`). Mọi LLM call đi qua adapter. Config `adapters.default = "mock"` — đổi model = đổi YAML.
- **Adapters:** `ClaudeAdapter`, `GPTAdapter`, `GeminiAdapter`, `LocalLLMAdapter`, `MockAdapter`. Thêm adapter mới = implement protocol, register trong config.
- **Mặc định:** `extraction.llm_enabled=false`. LLM chỉ bật cho case rule không cover. MVP không gọi LLM thật.
- **Test:** CI bắt buộc dùng `MockAdapter` — không test nào gọi API thật. Prompt test bằng golden file.

## Consequences

- (+) True model independence, future-proof khi vendor đổi.
- (+) Cost control: rule-first, batching, cache `hash(content)`, budget guard 50k tokens/run (chi tiết trong extraction engine).
- (-) Phải maintain prompt template per-adapter (Jinja2) và calibration.
- (-) `MockAdapter` cần golden data để test meaningful.

## Alternatives Considered

- **LiteLLM unified API:** tiện nhưng thêm dependency, vẫn cần adapter cho ContextPackage formatting.
- **Hardcode OpenAI:** đơn giản ban đầu nhưng lock-in, vi phạm nguyên tắc Model Independence.
- **LLM cho mọi extraction:** tốn kém, không cần thiết khi rule-based đã cover 80% code entities.
