# Engine 3: Knowledge Extraction Engine

> Execution Capability: Convert information into explicit, structured knowledge.
> [[glossary]]

---

## Role

Take normalized raw data (from Engines 1 & 2) and extract structured knowledge objects -- entities, relationships, decisions, and business rules -- with confidence scores.

---

## Extraction Pipeline

```
Normalized Raw Data (from Engines 1 & 2)
           |
           v
+--------------------------+
|  Pass 1: Rule-Based      |  Pattern matching for clear, structured data
|  Extraction              |  - ADR detection in Confluence pages
|                          |  - Class/function extraction from AST (Engine 2)
|                          |  - Requirement fields from Jira issues
|                          |  - API endpoint extraction from OpenAPI specs
+--------------------------+
           |
           v
+--------------------------+
|  Pass 2: LLM-Assisted    |  For ambiguous or unstructured content
|  Extraction              |  - Extract business rules from prose
|                          |  - Identify cross-reference relationships
|                          |  - Summarize long documents into key facts
|                          |  - Detect implicit dependencies
+--------------------------+
           |
           v
+--------------------------+
|  Pass 3: Confidence      |  Score each extracted fact
|  Scoring                 |  - Rule-based facts: high confidence
|                          |  - LLM-extracted facts: moderate confidence
|                          |  - Cross-references: lower confidence (needs validation)
+--------------------------+
           |
           v
KnowledgeObjects (with confidence scores, lifecycle_state=EXTRACTED)
           |
           v
       --> Engine 4 (Storage) for persistence
```

---

## What We Extract

| Type | Description | Example | Extraction Method | Typical Confidence |
|------|-------------|---------|-------------------|-------------------|
| `ENTITY` | Distinct thing in the project | `PaymentService`, `JIRA-123` | Rule-based + LLM | 0.8 - 1.0 |
| `RELATIONSHIP` | Connection between entities | `PaymentService IMPLEMENTS STORY-123` | Rule-based | 0.9 - 1.0 |
| `DECISION` | Architecture or design decision | "We chose Kafka for async processing" | LLM-assisted | 0.6 - 0.8 |
| `BUSINESS_RULE` | Constraint or policy | "Payments under $10 skip verification" | LLM-assisted | 0.5 - 0.7 |
| `CONCEPT` | Domain concept or term | "Idempotency key", "Circuit breaker" | LLM-assisted | 0.4 - 0.6 |

---

## Rule-Based Patterns

### ADR Detection (Confluence)
```
Pattern: Page contains "ADR" in title AND has sections:
  - Decision
  - Status (Proposed|Accepted|Deprecated)
  - Consequences
  => Extract as DECISION entity with ADR type
```

### Jira Requirement Extraction
```
Pattern: Issue type = Story/Task AND has acceptance criteria
  => Extract as REQUIREMENT entity
  => Link to parent Epic via REQUIRES relationship
```

### OpenAPI Endpoint Extraction
```
Pattern: OpenAPI spec with paths and methods
  => Extract ENDPOINT entity for each path+method combination
  => Extract API entity grouping by path prefix
```

### AST Code Entities (from Engine 2)
```
Pattern: AST node types (ClassDeclaration, FunctionDeclaration, etc.)
  => Extract as CodeEntity with appropriate kind
  => Build DEPENDS_ON and CALLS relationships from import/call nodes
```

---

## LLM-Assisted Extraction Prompts

### Business Rule Extraction
```
Extract all business rules from the following document.
A business rule is a constraint, policy, or requirement that governs
how the system must behave.

Document:
{content}

Return JSON array of rules:
[
  {
    "rule": "string",
    "applicable_to": "entity_or_module_name",
    "confidence": 0.0-1.0
  }
]
```

### Cross-Reference Detection
```
Identify relationships between these knowledge entities:
{entity_list}

Return JSON array of relationships:
[
  {
    "from": "entity_id",
    "to": "entity_id",
    "type": "DEPENDS_ON|CALLS|USES|IMPLEMENTS|...",
    "confidence": 0.0-1.0
  }
]
```

---

## Confidence Model

| Confidence | Range | Source | Treatment |
|------------|-------|--------|-----------|
| **High** | > 0.8 | Rule-based extraction from structured sources | Trust for most queries; include in all results |
| **Medium** | 0.5 - 0.8 | LLM-assisted extraction with clear signal | Include but flag in context; prefer over low |
| **Low** | < 0.5 | Ambiguous extraction or weak signal | Include in retrieval but mark for human review; exclude from summary queries |

Confidence can be boosted or demoted:
- **Boost**: Knowledge from authoritative source (Git code > Confluence doc for implementation facts)
- **Demote**: Knowledge that conflicts with higher-confidence knowledge

### Calibration (Bắt buộc)

Confidence do LLM tự gán thường over-confident. Mỗi LLM adapter phải có calibration:
- **Rule-based = 1.0** (không cần calibrate)
- **LLM:** lưu cặp `(llm_raw_confidence, human_verified_accuracy)` cho 100 sample đầu tiên; hiệu chỉnh bằng isotonic regression hoặc đơn giản `calibrated = raw * 0.8 + 0.1` cho đến khi có dữ liệu. Đánh giá calibration qua `docs/core/8-evaluation-framework.md` (reliability diagram).

---

## Cost Control — LLM Không Phải Là Pass Mặc Định

> **Rủi ro:** 3-pass pipeline nếu gọi LLM cho mọi RawItem sẽ cháy token.

**Quy tắc chi phí:**
1. **Rule-first, LLM-only-if-needed:** MVP *không gọi LLM* (Day 12-13 mock). Full mới bật LLM cho các case rule không cover (long prose, implicit dependencies). Mặc định `llm_enabled=false` trong config.
2. **Batching:** Gom 10-20 RawItems thành 1 prompt (giảm overhead system prompt). Max batch tokens = 4000.
3. **Caching:** Cache `hash(content) → ExtractionOutput` trong Metadata Store (`extraction_cache` table, TTL 7 ngày). Hit thì không gọi LLM.
4. **Budget guard:** `config.extraction.llm_budget_per_run` (ví dụ: 50k tokens/run). Vượt ngưỡng → dừng LLM, log warning, phần còn lại chỉ chạy rule-based.
5. **MockAdapter cho CI:** `pytest` bắt buộc dùng `MockAdapter` (không gọi API thật) — test LLM prompt bằng golden file, không bằng live call.
6. **Metrics:** Mỗi run ghi `llm_calls, prompt_tokens, completion_tokens, cost_usd` vào `extraction_stats` và expose qua `pkh status`.

```yaml
extraction:
  llm_enabled: false          # bật true chỉ khi cần
  llm_adapter: mock            # mock | openai | claude | gemini | local
  batch_size: 15
  cache_ttl_days: 7
  budget_per_run_tokens: 50000
  fallback: rule_only          # nếu LLM fail thì chỉ trả về rule-based
```

---

## Output

```python
class ExtractionOutput(BaseModel):
    entities: list[KnowledgeObject]       # object_type = ENTITY
    relationships: list[KnowledgeObject]  # object_type = RELATIONSHIP
    decisions: list[KnowledgeObject]      # object_type = DECISION
    rules: list[KnowledgeObject]          # object_type = BUSINESS_RULE
    stats: ExtractionStats
```

```python
class ExtractionStats(BaseModel):
    inputs_processed: int
    entities_extracted: int
    relationships_extracted: int
    decisions_extracted: int
    rules_extracted: int
    avg_confidence: float
    llm_calls: int
    duration_seconds: float
```