# ADR-004: LLM Adapter (Strategy) + Mock-First + LLM Off By Default

Date: 2026-09-06
Status: Accepted
Related: docs/engines/knowledge-extraction-engine.md, docs/engines/context-delivery-engine.md

## Context

PKH tuyên bố "Model Independence" — phải swap LLM bằng config, không đổi code. Đồng thời LLM API tốn tiền và confidence do LLM gán thường over-confident.

## Decision

- **Pattern:** Strategy `ModelAdapter` protocol (`complete`, `format_context`/`adapt`, `parse_response`, `get_token_limit`, `embed`). Mọi LLM call đi qua adapter. Config `adapters.default = "mock"` — đổi model = đổi YAML.
- **Adapters:** `ClaudeAdapter`, `GPTAdapter`, `GeminiAdapter`, `LocalLLMAdapter`, `MockAdapter`, `OpenAICompatibleAdapter` (`custom`, alias `CustomAdapter`, `src/pkh/adapters/custom.py`). Thêm adapter mới = implement protocol, register trong config.
- **Custom OpenAI-compatible provider (no mock):** `base_url + model + api_key` — dùng được với OpenAI, Azure OpenAI (qua base_url), OpenRouter, Ollama, vLLM, LM Studio hoặc bất kỳ server nào expose `POST {base_url}/chat/completions` + `POST {base_url}/embeddings`. Chọn qua shortcut `adapters.custom_*` hoặc named entry `adapters.providers.<name>` + `adapters.default = "<name>"` / `"provider:<name>"` / `get_adapter("custom"|"provider:<name>")`. API key ưu tiên env (`PKH_CUSTOM_API_KEY` / `OPENAI_API_KEY`, named: `PKH_ADAPTERS__PROVIDERS__<NAME>__API_KEY`), không commit secret. Lỗi HTTP/payload lỗi raise `AdapterError` (không fallback silent sang mock).
- **Mặc định:** `extraction.llm_enabled=false`. LLM chỉ bật cho case rule không cover (`extraction.llm_adapter: "mock"` → đổi sang `"custom"` / `"provider:<name>"` khi cần enrichment thật). MVP không gọi LLM thật.
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
