# Day 25 — Model Adapters (Phase 6)

> **Phase:** 6 — Context Delivery Engine | **Date:** Day 25 of 30 | **Goal:** Implement model-agnostic adapters for context delivery

---

## 🎯 Daily Target

**Deliverable:** ModelAdapter interface with concrete implementations (Claude, GPT, Gemini, Local, Mock) and config-driven switching

---

## ✅ Tasks

### 1. Define ModelAdapter Interface (`adapters.py`)
- [ ] Abstract base class with methods:
  - `async def complete(self, context: ContextPackage, model_config: dict) -> str`
  - `def format_context(self, context: ContextPackage) -> str`
  - `def parse_response(self, response: str) -> dict`
  - `def get_token_limit(self, model_config: dict) -> int`
- [ ] Protocol-based design for true model independence
- [ ] Configurable model types via enum or string identifiers

### 2. Implement ClaudeAdapter (Primary Adapter)
- [ ] Uses system prompt + messages array format
- [ ] Handles token limits via context truncation
- [ ] Configurable via `claude: ClaudeAdapterConfig` (model, api_key_env, max_tokens)
- [ ] Rate limiting integration
- [ ] Deterministic responses with low temperature (0.1)

### 3. Implement Other Adapters
- [ ] `GPTAdapter`: JSON instructions + messages + tools
- [ ] `GeminiAdapter`: text-focused format with examples
- [ ] `LocalLLMAdapter`: plain text format for local models
- [ ] `MockAdapter`: deterministic responses for testing

### 4. Config-Driven Adapter Selection
- [ ] `adapters.default = "openai"` (or "claude", etc.)
- [ ] Load config from `config.yaml` or env vars
- [ ] Factory function to instantiate correct adapter
- [ ] Fallback to MockAdapter if config invalid

### 5. Unit Tests (`tests/unit/test_adapters.py`)
- [ ] Test each adapter's `complete()` method
- [ ] Verify token limit calculation
- [ ] Verify response parsing
- [ ] Test MockAdapter for predictable behavior
- [ ] Test config-driven adapter selection

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| ModelAdapter interface defines all required methods | ☐ |
| ClaudeAdapter implements system prompt + messages | ☐ |
| All adapters implement required interface | ☐ |
| Config-driven adapter selection works | ☐ |
| Unit tests pass for all adapters | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 26 (Context streaming), Day 26 (ContextValidator)
- **Blocked by:** Day 24 (Context assembler)

---

## 📝 Notes

- Use `typing.Protocol` for interface definition
- Store adapter config in `adapters/config.yaml`
- Log adapter usage for monitoring
- Commit: `feat: model-agnostic adapters with config-driven selection`