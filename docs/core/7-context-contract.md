# Context Contract

> Engine 6: How we guarantee the quality and shape of context delivered to any LLM.
> [[glossary]]

---

## ContextPackage Structure

Every context delivered to an LLM follows the ContextContract. This is the canonical, model-agnostic format:

```python
class ContextPackage(BaseModel):
    """The contract between PKH and any LLM consumer."""
    
    # Required
    query: str                              # Original user query
    knowledge: list[KnowledgeChunk]         # Ranked knowledge snippets
    relationships: list[RelationshipChunk]  # Entity relationships
    confidence: float                       # Overall confidence (0.0-1.0)
    sources: list[SourceReference]          # Deduplicated source references
    lifecycle_states: list[str]             # Which states are represented
    
    # Optional
    warnings: list[str] = []                # e.g., "Low confidence results included"
    intent: str = ""                        # Classified intent type
    search_stats: SearchStats = None        # How many results per strategy
    compression_ratio: float = 1.0          # Original size / final size
```

```python
class KnowledgeChunk(BaseModel):
    """A single piece of knowledge in the context."""
    
    id: str                         # KnowledgeObject ID
    type: EntityType                # What kind of entity
    title: str                      # Human-readable title
    content: str                    # The actual knowledge text
    confidence: float               # 0.0 - 1.0
    lifecycle_state: LifecycleState # ACTIVE, UPDATED, etc.
    relevance_score: float          # How relevant to this query
    rank: int                       # Position in result set
    sources: list[SourceReference]  # Direct source links
```

```python
class RelationshipChunk(BaseModel):
    """A relationship between two knowledge entities."""
    
    from_id: str                    # Source entity ID
    to_id: str                      # Target entity ID
    type: RelationshipType          # DEPENDS_ON, CALLS, etc.
    confidence: float               # Confidence in this relationship
```

```python
class SearchStats(BaseModel):
    """Metrics about the retrieval process."""
    
    vector_results: int = 0
    keyword_results: int = 0
    graph_results: int = 0
    total_before_dedup: int = 0
    total_after_dedup: int = 0
    strategies_used: list[str] = []
    latency_ms: float = 0.0
```

---

## SLA Guarantees

| Guarantee | Description | Enforcement | Fallback |
|-----------|-------------|-------------|----------|
| **Token limit** | Context fits within model''s context window | Pre-compute token count; compress if needed | Tiered truncation: lowest confidence first |
| **Recency** | Only relevant-lifecycle knowledge returned | Filter by lifecycle state in retrieval | Include with `UPDATED`/`SUPERSEDED` warnings |
| **Traceability** | Every chunk links to its source | Validate SourceReference non-empty | Warning in ContextPackage.warnings |
| **Completeness** | All relevant relationships included | Graph traversal until saturation or hop limit | Surface "partial graph" notice |
| **Confidence** | Low-confidence items flagged | Min-confidence threshold configurable per engine | Lower threshold, add warning |
| **Latency** | Context delivered within target time | Per-strategy timeout + parallel execution | Return partial results |
| **Determinism** | Same query returns same context | Seed randomness, cache results | Cache miss triggers fresh retrieval |

---

## Model Adapters

The ContextPackage is the canonical format. Each model adapter converts it to the format that model expects:

```python
class ModelAdapter(Protocol):
    """Interface for converting ContextPackage to model-specific format."""
    
    def adapt(self, context: ContextPackage, model_config: dict) -> str:
        """Convert ContextPackage to model-ready prompt/text."""
        ...
    
    def parse_response(self, response: str) -> dict:
        """Parse model response back into structured format (optional)."""
        ...
    
    def get_token_limit(self, model_config: dict) -> int:
        """Return max context tokens for this model."""
        ...
```

### Adapter Specifications

| Model | Adapter Class | Format | Notes |
|-------|--------------|--------|-------|
| **Claude** | `ClaudeAdapter` | System prompt + messages array | Use `human`/`assistant` roles; include sources in system prompt |
| **GPT** | `GPTAdapter` | JSON instructions + messages | Structured output via JSON mode; tools for source references |
| **Gemini** | `GeminiAdapter` | Text with examples | Google-style prompting; multi-turn conversation support |
| **Local LLM** | `LocalLLMAdapter` | Plain text | No structured output; best-effort formatting |
| **Custom** | `CustomAdapter` | Configurable | Plugin system for any model format |

### Claude Adapter Example

```
You are a project knowledge assistant. Answer using ONLY the knowledge below.

## Knowledge
[KnowledgeChunk 1]
Title: PaymentService
Content: PaymentService handles all payment processing...
Confidence: 0.95
Source: https://github.com/.../PaymentService.java:42

[KnowledgeChunk 2]
...

## Relationships
PaymentService DEPENDS_ON PaymentGateway
PaymentService CALLS validateCard()

## Sources
- https://github.com/.../PaymentService.java
- https://org.atlassian.net/browse/PROJ-123

## Your Task
{query}

Answer based only on the knowledge above. Cite sources when possible.
If unsure, say so. Do not fabricate information.
```

### GPT Adapter Example

```json
{
  "messages": [
    {"role": "system", "content": "You are a project knowledge assistant..."},
    {"role": "user", "content": "{query}"},
    {"role": "assistant", "content": "..."}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_source",
        "description": "Get full source reference for a knowledge ID",
        "parameters": {
          "type": "object",
          "properties": {"knowledge_id": {"type": "string"}}
        }
      }
    }
  ]
}
```

---

## Context Compression Strategy

When the retrieved knowledge exceeds the model''s context window:

1. **Tier 1: Confidence-based pruning** -- Remove chunks with confidence < threshold
2. **Tier 2: Lifecycle-based pruning** -- Remove UPDATED/SUPERSEDED chunks (keep ACTIVE)
3. **Tier 3: Relevance-based truncation** -- Keep top-K by relevance_score
4. **Tier 4: Content compression** -- Summarize long chunks (use LLM to condense)
5. **Tier 5: Relationship pruning** -- Remove low-confidence relationships

Each tier is logged in `SearchStats` so the consumer knows what was compressed.

---

## Model-Agnostic Guarantee

```
                    ContextPackage (canonical, model-agnostic)
                    /         |         \         \
                   v          v          v          v
            ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
            │Claude    │ │GPT       │ │Gemini    │ │Local LLM │
            │Adapter    │ │Adapter    │ │Adapter    │ │Adapter    │
            └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Switching models = changing config only. No code changes. The ContextPackage structure never changes.