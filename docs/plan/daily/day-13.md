# Day 13 — LLM-Powered Extraction (Phase 3)

> **Phase:** 3 — Knowledge Extraction Engine | **Date:** Day 13 of 45 | **Goal:** Implement model-agnostic LLM extraction with adapter pattern

---

## 🎯 Daily Target

**Deliverable:** LLM-powered extraction adapter with OpenAI implementation and pluggable interface

---

## ✅ Tasks

### 1. Define Extraction Prompt Templates
- [ ] Create Jinja2 templates for:
  - Entity identification: "What entities are mentioned in this text?"
  - Relationship inference: "What relationships exist between these entities?"
  - Decision detection: "Is there an architecture decision or business rule?"
- [ ] Language-agnostic prompts with placeholders for:
  - Source type (code, document, requirement)
  - Content chunk
  - Context (surrounding entities)
- [ ] Output format: structured JSON with fallback parsing

### 2. Implement LLMExtractionAdapter Interface
- [ ] Abstract base class with methods:
  - `extract_entities(chunk: str) -> list[EntityCandidate]`
  - `extract_relationships(chunk: str, entities: list) -> list[RelationshipCandidate]`
  # noqa: E501
  - `detect_decisions_rules(chunk: str) -> list[DecisionRuleCandidate]`
- [ ] Structured output parsing with JSON mode / regex fallback
- [ ] Error handling for malformed LLM responses
- [ ] Retry logic with exponential backoff

### 3. Implement OpenAIAdapter
- [ ] Use OpenAI API with `response_format={"type": "json_object"}`
- [ ] Model: gpt-4o-mini (cost-effective) or gpt-3.5-turbo
- [ ] Temperature: 0.1 for deterministic extraction
- [ ] Max tokens: configurable per prompt type
- [ ] API key from environment variable (OPENAI_API_KEY)
- [ ] Rate limiting and token usage tracking

### 4. Implement MockAdapter for Testing
- [ ] Deterministic responses based on input patterns
- [ ] Configurable extraction results for test scenarios
- [ ] Simulate various LLM failure modes

### 5. Prompt Caching and Optimization
- [ ] Cache frequent prompt+input combinations
- [ ] Batch similar chunks for efficiency
- [ ] Token counting to stay within limits
- [ ] Fallback to rule-based extraction on LLM failure

### 6. Unit Tests
- [ ] Test OpenAIAdapter with mocked API responses
- [ ] Test MockAdapter for deterministic output
- [ ] Test prompt template rendering
- [ ] Test structured JSON parsing and fallback
- [ ] Test error handling and retries

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| OpenAIAdapter calls API with correct parameters | ☐ |
| Structured JSON output parsed correctly | ☐ |
| Fallback to regex parsing on JSON failure | ☐ |
| MockAdapter provides deterministic output | ☐ |
| Entity and relationship extraction works | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 14 (Decision & Rule Detection), Day 15 (Pipeline)
- **Blocked by:** Day 12 (Rule-based extraction provides candidates)

---

## 📝 Notes

- Use `openai` library v1.0+ with async support
- Prompt templates should be stored in `resources/prompts/`
- Log LLM token usage and cost for monitoring
- Commit: `feat: llm extraction adapter with openai implementation and mock`