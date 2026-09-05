# Retrieval Strategy

> Engine 5: How we find the right knowledge at the right time.
> [[glossary]]

---

## Retrieval Pipeline

```
User Query
    |
    v
+------------------+
|  1. Intent       |  Classify: code understanding / requirement traceability /
|     Detection    |  architecture / impact analysis / bug investigation / API usage
+------------------+
    |
    v
+------------------+
|  2. Query        |  Decompose: break complex queries into sub-queries
|     Planning     |  e.g., "What breaks if I change PaymentService?"
|                  |  -> "What depends on PaymentService?" + "What is PaymentService?"
+------------------+
    |
    v
+------------------+
|  3. Hybrid       |  Run multiple strategies in parallel:
|     Retrieval    |  - Vector search (semantic)
|                  |  - Keyword search (exact)
|                  |  - Graph traversal (relational)
+------------------+
    |
    v
+------------------+
|  4. Reranking    |  Re-score results using relevance signals:
|                  |  - Confidence score
|                  |  - Lifecycle state (prefer ACTIVE)
|                  |  - Recency (prefer recently updated)
|                  |  - Source authority (code > docs > requirements)
+------------------+
    |
    v
+------------------+
|  5. Deduplication|  Merge overlapping results from different strategies
|                  |  Keep highest-confidence version of each fact
+------------------+
    |
    v
Relevant Knowledge Set --> passed to Engine 6 (Context Delivery)
```

---

## Retrieval Strategies Deep Dive

### 1. Vector Search (Semantic)

How it works: Knowledge chunks are embedded using a text embedding model. Queries are also embedded. Results are ranked by cosine similarity.

Best for:
- "How does authentication work in this project?"
- "Find all knowledge about payment processing"
- "What are the security considerations?"

Configuration:
```yaml
retrieval:
  vector:
    model: "text-embedding-3-small"
    top_k: 20
    threshold: 0.75
    chunk_size: 512
    chunk_overlap: 64
```

### 2. Keyword Search (Exact)

How it works: Full-text inverted index over knowledge content. Supports boolean operators, phrase matching, and fuzzy matching.

Best for:
- "Find class PaymentService"
- "Show me all Jira issues in PROJ-123"
- "Search for exact string 'idempotency key'"

Configuration:
```yaml
retrieval:
  keyword:
    fields: ["title", "description", "content", "tags"]
    boost_title: 2.0
    boost_tags: 1.5
    fuzzy_threshold: 0.3
```

### 3. Graph Traversal (Relational)

How it works: Start from seed entities, follow relationships up to N hops. Returns all entities and relationships within the traversal radius.

Best for:
- "What does PaymentService depend on?"
- "Show me everything related to the auth module"
- "Trace from this bug to the affected code"

Configuration:
```yaml
retrieval:
  graph:
    max_hops: 3
    expand_relationships: ["DEPENDS_ON", "CALLS", "USES", "AFFECTS", "IMPLEMENTS"]
    prune_by_lifecycle: true
```

### 4. Hybrid Fusion

How it works: Combine results from all three strategies using weighted fusion. Each strategy produces a scored list; results are merged using Reciprocal Rank Fusion (RRF) or learned weighting.

Fusion formula (RRF):
```
score(result) = sum_over_strategies( 1 / (k + rank_in_strategy) )
```
where k is a constant (typically 60) and rank is the position in that strategy's results.

Strategy selection by intent:

| Intent | Primary | Secondary | Tertiary |
|--------|---------|-----------|----------|
| Code understanding | Vector | Graph | Keyword |
| Requirement traceability | Graph | Keyword | Vector |
| Architecture decision | Vector | Keyword | Graph |
| Impact analysis | Graph | Vector | Keyword |
| Bug investigation | Keyword | Vector | Graph |
| API usage | Keyword | Graph | Vector |
| Multi-part query | Graph + Vector | Keyword | |

---

## Intent Classification

Queries are classified into intent types before retrieval planning:

| Query Type | Example | Primary Strategy | Expected Output |
|------------|---------|------------------|-----------------|
| CODE_UNDERSTANDING | "How does PaymentService work?" | Vector + Graph | Code entities + relationships |
| REQUIREMENT_TRACEABILITY | "Which stories implement the auth feature?" | Graph + Keyword | Story -> Code mapping |
| ARCHITECTURE | "Why did we choose Kafka?" | Vector | Decision documents + rationale |
| IMPACT_ANALYSIS | "What breaks if I change the payment DB?" | Graph traversal | Affected services + code |
| BUG_INVESTIGATION | "Why is the checkout failing?" | Keyword + Vector | Related issues + code + logs |
| API_USAGE | "How do I call the payment API?" | Keyword + Graph | Endpoint specs + examples |
| COMPARISON | "Compare Stripe vs PayPal integration" | Vector + Keyword | Side-by-side knowledge |
| SUMMARY | "Summarize the payment module" | Vector | High-level overview |

Intent classification can be:
- Rule-based (keyword matching for simple cases)
- LLM-assisted (send query to LLM for classification)
- Hybrid (rules first, LLM fallback)

---

## Quality Guarantees

| Guarantee | Mechanism | Fallback |
|-----------|-----------|----------|
| Token limit | Results compressed to fit model window | Tiered truncation: lowest confidence first |
| Recency | Filter by lifecycle state (exclude DEPRECATED) | Include with UPDATED/SUPERSEDED warnings |
| Traceability | Every chunk has SourceReference | Warning in ContextPackage.warnings |
| Completeness | Graph traversal until saturation | Limit hops, surface gap notice |
| Confidence | Min-confidence threshold per strategy | Lower threshold, add warning |
| Latency | Parallel strategy execution | Timeout per strategy, partial results |