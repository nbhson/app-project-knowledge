# Day 26 — Context Contract & Streaming (Phase 6)

> **Phase:** 6 — Context Delivery Engine | **Date:** Day 26 of 30 | **Goal:** Implement context validation, streaming, caching, and SLA enforcement

---

## 🎯 Daily Target

**Deliverable:** Context validator, streaming support, caching, and rate limiting with SLA guarantees

---

## ✅ Tasks

### 1. ContextValidator
- [ ] Validate output against contract (`core/7-context-contract.md`):
  - All chunks have SourceReference
  - All confidence scores are valid (0.0-1.0)
  - Lifecycle states are included and valid
  - No null/empty required fields
- [ ] Raise `ValidationError` on contract violation
- [ ] Log validation warnings (not errors) for warnings

### 2. Streaming Support
- [ ] Generator/yield-based streaming for long contexts
- [ ] Chunked context delivery (e.g., 1000 tokens at a time)
- [ ] Callback hook for progress reporting
- [ ] Cancel-on-error for streaming failures

### 3. Context Caching with TTL
- [ ] LRU cache for context packages
- [ ] TTL-based expiration (configurable, default=5 minutes)
- [ ] Cache key: hash of query + filters + intent
- [ ] Cache hit rate metrics
- [ ] Background cleanup of expired entries

### 4. Rate Limiting per Model Adapter
- [ ] Per-adapter rate limiting (requests/minute)
- [ ] Configurable via `adapters.<model>.rpm` or environment
- [ ] Token-based limiting (tokens/minute)
- [ ] Queue with backpressure handling

### 5. SLA Enforcement
- [ ] Token limit enforcement (context must fit model's limit)
- [ ] Latency SLA: max 2 seconds for context preparation
- [ ] Determinism guarantee: same query → same context (within cache window)
- [ ] Timeout handling for slow operations

### 6. Integration Tests
- [ ] Test validation catches contract violations
- [ ] Test streaming delivers all chunks
- [ ] Test cache hit rate
- [ ] Test rate limiting
- [ ] Test SLA compliance

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| ContextValidator catches all contract violations | ☐ |
| Streaming delivers chunks correctly | ☐ |
| Cache with TTL works correctly | ☐ |
| Rate limiting per adapter works | ☐ |
| SLA enforcement (token limit, latency) | ☐ |
| Integration tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Phase 7 (CLI, API use context delivery)
- **Blocked by:** Day 24-25 (Context assembly, adapters)

---

## 📝 Notes

- Use `functools.lru_cache` with TTL wrapper
- Implement rate limiting via `asyncio.Semaphore`
- Streaming useful for chat-style interactions
- Commit: `feat: context validation, streaming, caching, and SLA enforcement`