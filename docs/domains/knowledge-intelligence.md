# Knowledge Intelligence Domain

> Domain 3: Find and reason over knowledge intelligently.
> Implements Engines 5 and 6.
> [[glossary]]

---

## Responsibility

The Knowledge Intelligence domain is the "brain" of the system. It understands user intent, plans retrieval strategies, finds the most relevant knowledge from the Knowledge Core, and assembles model-ready context packages. This domain bridges the gap between raw knowledge and actionable answers.

### Core Responsibilities

1. **Understand intent** — Classify queries into 8 intent types to select the right retrieval strategy
2. **Plan queries** — Decompose complex multi-part queries into sub-queries
3. **Retrieve intelligently** — Run vector, keyword, and graph search in parallel with RRF fusion
4. **Rerank and deduplicate** — Score results by confidence, recency, lifecycle, and relevance
5. **Assemble context** — Build ContextPackage that fits any LLM's context window
6. **Guarantee quality** — Validate every output against the Context Contract SLAs

---

## Engines in This Domain

| Engine | Role | Input | Key Output |
|--------|------|-------|------------|
| **5. Retrieval Intelligence** | Find relevant knowledge | User query | RelevantKnowledgeSet (ranked, deduplicated) |
| **6. Context Delivery** | Assemble model-ready context | RelevantKnowledgeSet | ContextPackage (model-agnostic) |

---

## Data Flow

```
User Query (natural language)
         |
         v
+---------------------------+
|  Engine 5:               |
|  Retrieval Intelligence  |--> RelevantKnowledgeSet
|  - Intent Detection      |     (ranked, deduplicated)
|  - Query Planning        |
|  - Hybrid Retrieval      |
|  - Reranking             |
|  - Deduplication         |
+---------------------------+
         |
         v
+---------------------------+
|  Engine 6:               |
|  Context Delivery        |--> ContextPackage
|  - Context Assembly      |     (model-agnostic)
|  - Compression           |
|  - Contract Validation   |
|  - Model Adapters        |
+---------------------------+
         |
         v
    Any LLM / Consumer
```

---

## Domain Boundaries

### Inputs (from outside the domain)

- **User queries** — Natural language questions from CLI, API, or agents
- **RelevantKnowledgeSet** — Raw retrieval results from Engine 5 (internal handoff)
- **Knowledge Core** — Read access to all 4 storage layers (Vector, Graph, Metadata, Raw)
- **Model configuration** — Target LLM selection and adapter config

### Outputs (to the rest of the system)

- **ContextPackage** — Model-agnostic context for any LLM consumer
- **SearchStats** — Metrics about retrieval performance (latency, strategy usage, compression)
- **User answers** — Natural language responses powered by LLM using the context
- **Feedback signals** — User ratings that feed back into retrieval tuning

### What this domain does NOT do

- Does NOT ingest or store knowledge (that is Domain 1 & 2)
- Does NOT modify the Knowledge Core directly
- Does NOT serve consumers directly (that is Domain 4)
- Does NOT make LLM calls itself — delegates to Model Adapters

---

## Retrieval Pipeline (Engine 5)

### Step 1: Intent Detection

Classifies the query into one of 8 intent types:

| Intent | Example Query | Primary Strategy |
|--------|---------------|------------------|
| `CODE_UNDERSTANDING` | "How does PaymentService work?" | Vector + Graph |
| `REQUIREMENT_TRACEABILITY` | "Which stories implement auth?" | Graph + Keyword |
| `ARCHITECTURE` | "Why did we choose Kafka?" | Vector |
| `IMPACT_ANALYSIS` | "What breaks if I change the DB?" | Graph traversal |
| `BUG_INVESTIGATION` | "Why is checkout failing?" | Keyword + Vector |
| `API_USAGE` | "How do I call the payment API?" | Keyword + Graph |
| `COMPARISON` | "Compare Stripe vs PayPal" | Vector + Keyword |
| `SUMMARY` | "Summarize the payment module" | Vector |

Implementation: Rule-based keyword matching + LLM fallback for ambiguous queries.

### Step 2: Query Planning

For complex queries, decompose into sub-queries:

```
Original: "What breaks if I change PaymentService?"

Sub-queries:
1. "What does PaymentService depend on?" (graph traversal)
2. "What depends on PaymentService?" (reverse graph traversal)
3. "What is PaymentService's database configuration?" (vector + keyword)
```

### Step 3: Hybrid Retrieval

All three strategies run in parallel:

| Strategy | Purpose | Best For |
|----------|---------|----------|
| **Vector** | Semantic similarity | "Find knowledge about X" |
| **Keyword** | Exact match | "Find class PaymentService" |
| **Graph** | Relationship traversal | "What depends on X?" |

Fusion uses Reciprocal Rank Fusion (RRF):
```
score(result) = sum_over_strategies( 1 / (k + rank_in_strategy) )
```
where k = 60 (default).

### Step 4: Reranking

Re-score using weighted signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| `confidence` | 0.3 | KnowledgeObject confidence score |
| `lifecycle_bonus` | 0.2 | ACTIVE = +1.0, UPDATED = +0.5, others = 0 |
| `recency` | 0.1 | Recent knowledge gets slight boost |
| `source_authority` | 0.1 | Code > Docs > Requirements |
| `relevance_score` | 0.3 | Original retrieval score |

### Step 5: Deduplication

When multiple strategies return the same KnowledgeObject, keep only the highest-scoring version.

---

## Context Assembly (Engine 6)

### ContextPackage Structure

```python
class ContextPackage(BaseModel):
    query: str                              # Original user query
    knowledge: list[KnowledgeChunk]         # Ranked knowledge snippets
    relationships: list[RelationshipChunk]  # Entity relationships
    confidence: float                       # Overall confidence (0.0-1.0)
    sources: list[SourceReference]          # Deduplicated source references
    lifecycle_states: list[str]             # Which states are represented
    warnings: list[str] = []                # e.g., "Low confidence results included"
    intent: str = ""                        # Classified intent type
    search_stats: SearchStats = None        # How many results per strategy
    compression_ratio: float = 1.0          # Original size / final size
```

### Context Compression (5 Tiers)

| Tier | Strategy | When Applied | Impact |
|------|----------|--------------|--------|
| 1 | Confidence pruning | Remove chunks with confidence < threshold | Low quality removed first |
| 2 | Lifecycle pruning | Remove UPDATED/SUPERSEDED chunks | Keep only current knowledge |
| 3 | Relevance truncation | Keep top-K by relevance_score | Most relevant preserved |
| 4 | Content summarization | Use LLM to condense long chunks | Retains meaning, reduces tokens |
| 5 | Relationship pruning | Remove low-confidence relationships | Keeps core structure |

---

## Model Adapters

The ContextPackage is the canonical, model-agnostic format. Each adapter converts it to the target LLM's format:

| Model | Adapter | Format |
|-------|---------|--------|
| **Claude** | `ClaudeAdapter` | System prompt + messages array |
| **GPT** | `GPTAdapter` | JSON instructions + messages + tools |
| **Gemini** | `GeminiAdapter` | Text with examples |
| **Local LLM** | `LocalLLMAdapter` | Plain text |
| **Custom** | `CustomAdapter` | Configurable plugin system |

Switching models = changing config only. No code changes.

---

## SLA Guarantees

| Guarantee | Target | Enforcement | Fallback |
|-----------|--------|-------------|----------|
| **Token limit** | Context fits model window | Pre-compute token count; compress if needed | Tiered truncation |
| **Latency** | < 500ms for 10K objects | Parallel strategy execution + per-strategy timeout | Return partial results |
| **Traceability** | Every chunk has SourceReference | Validate on assembly | Warning in ContextPackage |
| **Confidence** | Low-confidence items flagged | Min-confidence threshold per strategy | Lower threshold + warning |
| **Recency** | Only relevant lifecycle knowledge | Filter by lifecycle state | Include with warnings |
| **Determinism** | Same query returns same context | Seed randomness + cache | Cache miss triggers fresh |

---

## Quality Gates

Before context leaves this domain:

| Gate | Check | Action if Failed |
|------|-------|-----------------|
| Token limit respected | Token count <= model limit | Tier 1-5 compression |
| All chunks have sources | Non-empty SourceReference | Warning; do not block delivery |
| Lifecycle states valid | No DEPRECATED/ARCHIVED included | Filter before delivery |
| Confidence calibrated | Warnings for < 0.5 chunks | Flag in ContextPackage.warnings |
| Latency target met | Total pipeline < 500ms | Return partial results with warning |

---

## Configuration

```yaml
domain: knowledge_intelligence
engines:
  retrieval:
    top_k: 10
    min_confidence: 0.3
    hybrid: true
    rerank: true
    fusion:
      method: rrf
      k: 60
    strategies:
      vector:
        enabled: true
        top_k: 20
        threshold: 0.75
      keyword:
        enabled: true
        boost_title: 2.0
      graph:
        enabled: true
        max_hops: 3
        relations: [DEPENDS_ON, CALLS, USES, AFFECTS, IMPLEMENTS]
    reranking:
      confidence_weight: 0.3
      lifecycle_weight: 0.2
      recency_weight: 0.1
      relevance_weight: 0.4
  
  context_delivery:
    max_tokens: 128000
    tier_thresholds:
      confidence_min: 0.3
      lifecycle_exclude: [SUPERSEDED, DEPRECATED, ARCHIVED]
    validation:
      require_sources: true
      max_warnings: 5
      fail_on_critical: true
```

---

## Error Handling

| Error Type | Recovery |
|------------|----------|
| Vector store timeout | Fall back to keyword + graph only |
| Graph traversal timeout | Return vector + keyword results with partial notice |
| LLM classification failure | Use rule-based keyword matching fallback |
| Context exceeds token limit | Apply all 5 compression tiers |
| Source unreachable | Include warning; deliver without that source |
| Adapter not configured | Return raw ContextPackage for manual handling |
