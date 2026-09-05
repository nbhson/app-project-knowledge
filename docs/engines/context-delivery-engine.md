# Engine 6: Context Delivery Engine

> Execution Capability: Assemble model-ready context packages, model-agnostic.
> [[glossary]]

---

## Role

Take retrieval results and assemble them into a ContextPackage that any LLM can consume, with quality guarantees. This is the final step before the knowledge reaches the consumer.

---

## Pipeline

```
RelevantKnowledgeSet (from Engine 5)
         |
         v
+---------------------------+
|  1. Context Assembly      |  Build ContextPackage structure
|                             |  - Format knowledge chunks
|                             |  - Format relationship chunks
|                             |  - Collect source references
|                             |  - Compute overall confidence
+---------------------------+
         |
         v
+---------------------------+
|  2. Context Compression   |  Fit within model token limit
|                             |  - Tiered pruning (see below)
|                             |  - Log what was compressed
+---------------------------+
         |
         v
+---------------------------+
|  3. Contract Validation   |  Check SLA guarantees
|                             |  - Token limit respected?
|                             |  - All chunks have sources?
|                             |  - Lifecycle states valid?
|                             |  - Confidence flagged where needed?
+---------------------------+
         |
         v
+---------------------------+
|  4. Model Adapter         |  Convert to target LLM format
|                             |  - Claude: system prompt + messages
|                             |  - GPT: JSON + tools
|                             |  - Gemini: text + examples
|                             |  - Local: plain text
+---------------------------+
         |
         v
ContextPackage --> Any LLM / Consumer
```

---

## Context Assembly

Transforms the RelevantKnowledgeSet into the canonical ContextPackage:

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
    id: str                         # KnowledgeObject ID
    type: EntityType                # What kind of entity
    title: str                      # Human-readable title
    content: str                    # The actual knowledge text
    confidence: float               # 0.0 - 1.0
    lifecycle_state: LifecycleState # ACTIVE, UPDATED, etc.
    relevance_score: float          # How relevant to this query
    rank: int                       # Position in result set
    sources: list[SourceReference]  # Direct source links

class RelationshipChunk(BaseModel):
    from_id: str                    # Source entity ID
    to_id: str                      # Target entity ID
    type: RelationshipType          # DEPENDS_ON, CALLS, etc.
    confidence: float               # Confidence in this relationship
```

---

## Context Compression Strategy

When retrieved knowledge exceeds the model''s context window:

| Tier | Strategy | When Applied | Impact |
|------|----------|--------------|--------|
| 1 | Confidence pruning | Remove chunks with confidence < threshold | Low quality removed first |
| 2 | Lifecycle pruning | Remove UPDATED/SUPERSEDED chunks | Keep only current knowledge |
| 3 | Relevance truncation | Keep top-K by relevance_score | Most relevant preserved |
| 4 | Content summarization | Use LLM to condense long chunks | Retains meaning, reduces tokens |
| 5 | Relationship pruning | Remove low-confidence relationships | Keeps core structure |

Each tier is logged in `SearchStats.compression_log`:
```python
class CompressionLog(BaseModel):
    tier: int
    strategy: str
    items_removed: int
    tokens_saved: int
    reason: str
```

---

## Contract Validation

Before delivering context, validate all SLA guarantees:

```python
class ContextValidator:
    """Validates ContextPackage against SLA guarantees."""
    
    def validate(self, package: ContextPackage) -> ValidationResult:
        warnings = []
        
        # 1. Token limit check
        token_count = self._count_tokens(package)
        if token_count > self._get_model_limit(package.intent):
            warnings.append(f"Context exceeds model limit by {token_count - limit} tokens")
        
        # 2. Traceability check
        missing_sources = [c for c in package.knowledge if not c.sources]
        if missing_sources:
            warnings.append(f"{len(missing_sources)} chunks missing source references")
        
        # 3. Lifecycle check
        deprecated = [c for c in package.knowledge 
                      if c.lifecycle_state in ("DEPRECATED", "ARCHIVED")]
        if deprecated:
            warnings.append(f"{len(deprecated)} deprecated chunks included (should be filtered)")
        
        # 4. Confidence check
        low_conf = [c for c in package.knowledge if c.confidence < 0.5]
        if low_conf:
            warnings.append(f"{len(low_conf)} low-confidence chunks included")
        
        return ValidationResult(
            valid=len(warnings) == 0,
            warnings=warnings,
            token_count=token_count
        )
```

---

## Model Adapters

Interface for converting ContextPackage to model-specific format:

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

| Model | Adapter Class | Format | Notes |
|-------|--------------|--------|-------|
| **Claude** | `ClaudeAdapter` | System prompt + messages array | Use `human`/`assistant` roles; include sources in system prompt |
| **GPT** | `GPTAdapter` | JSON instructions + messages | Structured output via JSON mode; tools for source references |
| **Gemini** | `GeminiAdapter` | Text with examples | Google-style prompting; multi-turn conversation support |
| **Local LLM** | `LocalLLMAdapter` | Plain text | No structured output; best-effort formatting |
| **Custom** | `CustomAdapter` | Configurable | Plugin system for any model format |

---

## Configuration

```yaml
context_delivery:
  model:
    default: claude-sonnet-4-20250514
    adapters:
      claude:
        class: ClaudeAdapter
        system_prompt_template: prompts/claude_system.j2
      gpt:
        class: GPTAdapter
        json_mode: true
      gemini:
        class: GeminiAdapter
      local:
        class: LocalLLMAdapter
        base_url: http://localhost:11434/v1
  
  compression:
    max_tokens: 128000        # Claude Sonnet context window
    tier_thresholds:
      confidence_min: 0.3
      lifecycle_exclude: ["SUPERSEDED", "DEPRECATED", "ARCHIVED"]
  
  validation:
    require_sources: true
    max_warnings: 5           # Still deliver context even with warnings
    fail_on_critical: true    # Fail if traceability broken
```