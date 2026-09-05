# Evaluation Framework

> How we measure whether the Harness is doing its job well.
> [[glossary]]

---

## Knowledge Quality Metrics

Measures the quality of knowledge stored in the Knowledge Core.

| Metric | Formula | Target | How to Measure |
|--------|---------|--------|----------------|
| **Coverage** | `indexed_entities / total_project_entities` | > 80% | Count entities from sources vs. expected |
| **Freshness** | `avg(age_of_last_sync)` per source type | < 24h | Query Metadata Store for last_synced timestamps |
| **Confidence avg** | `avg(confidence)` across all ACTIVE knowledge | > 0.7 | Aggregate from KnowledgeObjects |
| **Completeness** | `% of KnowledgeObjects with >= 1 SourceReference` | > 95% | Count objects with empty source_references |
| **Lifecycle compliance** | `% of non-archived knowledge with valid lifecycle state` | > 99% | Check for orphaned or invalid states |
| **Duplicate rate** | `% of KnowledgeObjects that are duplicates of another` | < 5% | Compare content hashes within same source |

---

## Retrieval Quality Metrics

Measures how well the Retrieval Intelligence Engine finds the right knowledge.

| Metric | Formula | Target | How to Measure |
|--------|---------|--------|----------------|
| **Precision@K** | `relevant_in_top_K / K` | > 0.8 | Human or automated labeling of results |
| **Recall@K** | `relevant_found / total_relevant` | > 0.7 | Compare against golden test set |
| **NDCG@K** | Normalized Discounted Cumulative Gain | > 0.75 | Rank-aware relevance scoring |
| **MRR** | Mean Reciprocal Rank | > 0.8 | Position of first relevant result |
| **Latency p50** | 50th percentile query latency | < 300ms | Timing middleware on retrieval engine |
| **Latency p99** | 99th percentile query latency | < 1000ms | Timing middleware on retrieval engine |
| **Cache hit rate** | `cached_queries / total_queries` | > 60% | Track cache lookups vs. misses |

### Test Protocol

```python
def evaluate_retrieval(test_cases: list[TestCase]) -> EvaluationResult:
    """Run retrieval evaluation against golden test cases."""
    results = []
    for tc in test_cases:
        query = tc.query
        expected_ids = set(tc.expected_knowledge_ids)
        
        # Run retrieval
        knowledge_set = retrieval_engine.retrieve(query, top_k=tc.top_k)
        found_ids = {ko.id for ko in knowledge_set.knowledge}
        
        # Compute metrics
        precision = len(expected_ids & found_ids) / len(found_ids) if found_ids else 0
        recall = len(expected_ids & found_ids) / len(expected_ids) if expected_ids else 0
        
        results.append({
            "query": query,
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0,
            "latency_ms": knowledge_set.search_stats.latency_ms,
        })
    
    return aggregate(results)
```

---

## Context Quality Metrics

Measures how well the Context Delivery Engine assembles usable context.

| Metric | Formula | Target | How to Measure |
|--------|---------|--------|----------------|
| **Token efficiency** | `useful_tokens / total_tokens_in_context` | > 0.6 | Estimate useful = content without metadata overhead |
| **Source coverage** | `% of KnowledgeChunks with valid SourceReference` | > 0.9 | Validate each chunk has non-empty sources |
| **Hallucination rate** | `unsupported_claims / total_claims_in_response` | < 0.05 | Sample LLM responses, check against source |
| **Context utilization** | `% of context tokens used by model in response` | > 0.4 | Compare input tokens to output token relevance |
| **Adaptation accuracy** | `% of contexts correctly formatted for target model` | > 99% | Parse/adapt round-trip validation |

---

## System Metrics

Measures operational health of the entire Harness.

| Metric | Formula | Alert Threshold | How to Measure |
|--------|---------|-----------------|----------------|
| **Ingestion rate** | `documents_processed / minute` | < 10 doc/min (suspicious) | Engine 1 pipeline counters |
| **Sync success rate** | `successful_syncs / total_sync_attempts` | < 95% | Connector health checks |
| **Error rate** | `failed_operations / total_operations` | > 1% | Structured error logging |
| **Cost per query** | `(embedding_tokens + llm_tokens) / query_count` | Track trend | API cost tracking |
| **Storage growth** | `kb_new_per_day` | Monitor trend | Database size metrics |
| **Uptime** | `available_time / total_time` | > 99.5% | Health check endpoint |

---

## Evaluation Feedback Loop

```
Retrieval Result
      |
      v
Human Feedback / Automated Check
      |  (thumbs up/down, correctness verification)
      v
Quality Score (per query, per metric)
      |
      v
Engine Tuning
      |  (adjust thresholds, weights, prompts)
      v
Improved Retrieval --> loop continues
```

**Continuous evaluation runs:**
1. **Daily automated tests** -- synthetic queries against known knowledge
2. **Weekly human review** -- sample of real queries evaluated by domain expert
3. **Monthly report** -- trend analysis across all metrics