# Engine 5: Retrieval Intelligence Engine

> Execution Capability: Find relevant knowledge intelligently.
> [[glossary]]

---

## Role

Understand the user intent, plan the retrieval strategy, and find the most relevant knowledge from the Knowledge Core. This is the "brain" of the retrieval pipeline.

---

## Pipeline

```
User Query (natural language)
         |
         v
+---------------------------+
|  1. Intent Detection      |  Classify query intent
|                             |  CODE_UNDERSTANDING | REQUIREMENT_TRACEABILITY |
|                             |  ARCHITECTURE | IMPACT_ANALYSIS | BUG_INVESTIGATION |
|                             |  API_USAGE | COMPARISON | SUMMARY
+---------------------------+
         |
         v
+---------------------------+
|  2. Query Planning        |  Decompose complex queries
|                             |  "What breaks if I change PaymentService?"
|                             |  -> Sub-query 1: "What depends on PaymentService?"
|                             |  -> Sub-query 2: "What is PaymentService?"
+---------------------------+
         |
         v
+---------------------------+
|  3. Hybrid Retrieval      |  Run multiple strategies in parallel
|                             |  - Vector search (semantic similarity)
|                             |  - Keyword search (exact match)
|                             |  - Graph traversal (relationship follow)
+---------------------------+
         |
         v
+---------------------------+
|  4. Reranking             |  Re-score all results together
|                             |  Signals: confidence, recency, lifecycle, relevance
+---------------------------+
         |
         v
+---------------------------+
|  5. Deduplication         |  Merge overlapping results
|                             |  Keep highest-confidence version of each fact
+---------------------------+
         |
         v
RelevantKnowledgeSet --> passed to Engine 6 (Context Delivery)
```

---

## Intent Detection

Classifies the user query into one of these intent types:

| Intent | Trigger Keywords/Patterns | Example Query |
|--------|--------------------------|---------------|
| `CODE_UNDERSTANDING` | "how does", "what is", "explain", "work" + code terms | "How does PaymentService work?" |
| `REQUIREMENT_TRACEABILITY` | "which", "implement", "trace", "connect" + story/issue terms | "Which stories implement auth?" |
| `ARCHITECTURE` | "why", "decision", "choice", "architecture" | "Why did we choose Kafka?" |
| `IMPACT_ANALYSIS` | "what breaks", "affects", "depend", "change" | "What breaks if I change the DB schema?" |
| `BUG_INVESTIGATION` | "why failing", "error", "bug", "issue" + symptom | "Why is checkout failing?" |
| `API_USAGE` | "how to call", "use", "endpoint", "api" | "How do I call the payment API?" |
| `COMPARISON` | "compare", "vs", "difference", "between" | "Compare Stripe vs PayPal" |
| `SUMMARY` | "summarize", "overview", "tell me about" | "Summarize the payment module" |

Implementation: Rule-based keyword matching + LLM fallback for ambiguous queries.

---

## Query Planning

For complex queries, decompose into sub-queries:

```
Original: "What breaks if I change the PaymentService database connection?"

Sub-queries:
1. "What does PaymentService depend on?" (graph traversal)
2. "What depends on PaymentService?" (reverse graph traversal)
3. "What is PaymentService's database configuration?" (vector + keyword)
4. "What are the known issues with PaymentService?" (keyword + lifecycle filter)
```

Each sub-query runs its own retrieval, then results are merged and deduplicated.

---

## Hybrid Retrieval Execution

All three strategies run in parallel. Each produces a ranked list:

```python
class RetrievalResult(BaseModel):
    strategy: str                    # "vector" | "keyword" | "graph"
    query: str
    results: list[KnowledgeChunk]
    stats: SearchStats
```

**Fusion (Reciprocal Rank Fusion):**
```python
def rrf_fuse(results: list[RetrievalResult], k: int = 60) -> list[KnowledgeChunk]:
    """Merge results from multiple strategies using RRF."""
    score_map = defaultdict(float)
    for rr in results:
        for rank, chunk in enumerate(rr.results, start=1):
            score_map[chunk.id] += 1.0 / (k + rank)
    
    # Sort by fused score
    sorted_ids = sorted(score_map, key=score_map.get, reverse=True)
    return [chunk for chunk_id in sorted_ids 
            for chunk in results if chunk.id == chunk_id]  # deduplicate
```

---

## Reranking

After fusion, re-score using additional signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| `confidence` | 0.3 | KnowledgeObject confidence score |
| `lifecycle_bonus` | 0.2 | ACTIVE = +1.0, UPDATED = +0.5, others = 0 |
| `recency` | 0.1 | Recent knowledge gets slight boost |
| `source_authority` | 0.1 | Code > Docs > Requirements for implementation facts |
| `relevance_score` | 0.3 | Original retrieval score |

```python
final_score = (
    0.3 * chunk.confidence +
    0.2 * lifecycle_bonus(chunk.lifecycle_state) +
    0.1 * recency_score(chunk.updated_at) +
    0.1 * source_authority(chunk.entity_type) +
    0.3 * chunk.relevance_score
)
```

---

## Deduplication

When multiple strategies return the same knowledge (same KnowledgeObject ID), keep only the highest-scoring version:

```python
def deduplicate(chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    seen = {}
    for chunk in chunks:
        if chunk.id not in seen or chunk.final_score > seen[chunk.id].final_score:
            seen[chunk.id] = chunk
    return sorted(seen.values(), key=lambda c: c.final_score, reverse=True)
```

---

## Output

```python
class RelevantKnowledgeSet(BaseModel):
    knowledge: list[KnowledgeChunk]           # Ranked, deduplicated
    relationships: list[RelationshipChunk]     # Related entity connections
    search_stats: SearchStats                  # How the search performed
    intent: str                                # Classified intent
    warnings: list[str]                        # e.g., "Partial results due to timeout"
```