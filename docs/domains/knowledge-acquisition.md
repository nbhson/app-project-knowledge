# Knowledge Acquisition Domain

> Domain 1: Collect raw project data and convert to normalized form.
> Implements Engines 1, 2, and 3.
> [[glossary]]

---

## Responsibility

The Knowledge Acquisition domain is responsible for turning raw project data from multiple sources into structured, confidence-scored knowledge objects ready for the Knowledge Core. It is the "ingest-and-understand" phase of the system.

### Core Responsibilities

1. **Connect** to all configured data sources (Git, Confluence, Jira, Documents, API specs)
2. **Understand** code structure at the AST level (symbols, dependencies, call graphs)
3. **Extract** explicit knowledge from raw information (entities, relationships, decisions, rules)
4. **Score** confidence for each piece of extracted knowledge
5. **Validate** that all output has source references and proper lifecycle state

---

## Engines in This Domain

| Engine | Role | Input | Key Output |
|--------|------|-------|------------|
| **1. Ingestion** | Connect, sync, normalize | Source APIs, file systems, webhooks | Normalized RawItems (lifecycle=DISCOVERED) |
| **2. Code Intelligence** | Parse code structure | Source code files | CodeEntities + CodeRelationships |
| **3. Knowledge Extraction** | Convert info to knowledge | RawItems + CodeEntities | KnowledgeObjects with confidence scores |

---

## Data Flow

```
Raw Sources (Git, Confluence, Jira, Documents)
          |
          v
+-------------------+
|  Engine 1:       |
|  Ingestion       |--> Normalized RawItems (DISCOVERED)
|  - Connectors    |
|  - Sync Manager  |
|  - Change Detect |
+-------------------+
          |
          +-----> (code files) ----> +-------------------+
          |                              |  Engine 2:      |
          |                              |  Code Intelli.  |--> CodeEntities
          |                              +-------------------+
          |                                          |
          |  (non-code docs)                         |
          +------------------------------------------+
                                                         v
                                              +-------------------+
                                              |  Engine 3:        |
                                              |  Extraction       |--> KnowledgeObjects (EXTRACTED)
                                              |  - Rule-based     |     (confidence scored)
                                              |  - LLM-assisted   |
                                              |  - Confidence     |
                                              +-------------------+
                                                         |
                                                         v
                                              Knowledge Core (Domain 2)
```

---

## Domain Boundaries

### Inputs (from outside the domain)
- Source system APIs (Git HTTP, Confluence REST, Jira REST)
- File system events (for local document watching)
- Webhook events (push events, page edits, issue updates)
- Configuration (which sources to sync, auth credentials)

### Outputs (to the rest of the system)
- **To Engine 2 (Code Intelligence):** RawItems that are source code files
- **To Engine 3 (Extraction):** RawItems for all source types + CodeEntities from Engine 2
- **To Storage (Engine 4):** KnowledgeObjects with lifecycle_state=EXTRACTED
- **To Update Loop:** Change detection results for staleness monitoring

### What this domain does NOT do
- Does NOT store knowledge (that is Domain 2 / Engine 4)
- Does NOT retrieve knowledge (that is Domain 3 / Engines 5 & 6)
- Does NOT serve consumers (that is Domain 4)

---

## Quality Gates

Before knowledge leaves this domain, it must pass ALL gates:

| Gate | Check | Action if Failed |
|------|-------|-----------------|
| Source reference | Every KnowledgeObject has >= 1 SourceReference | Reject; send back to Ingestion |
| Content non-empty | content field is not blank | Reject; log warning |
| Confidence assigned | confidence is set (0.0 - 1.0) | Default to 0.5 (LLM-extracted) or 1.0 (rule-based) |
| Lifecycle state valid | State is one of: DISCOVERED, EXTRACTED, VALIDATING | Reject; log error |
| Entity type recognized | object_type is in the Entity Taxonomy | Map to nearest known type; flag for review |
| Source accessible | SourceReference URL/path is reachable | Flag as "source unavailable"; keep knowledge |

---

## Error Handling

| Error Type | Recovery |
|------------|----------|
| Source API rate limit | Exponential backoff; retry after delay |
| Source API auth failure | Alert admin; skip source until fixed |
| Parse error (malformed code) | Log error; skip file; continue processing |
| LLM extraction failure | Fall back to rule-based extraction; mark confidence=0.3 |
| Network timeout | Retry 3x with backoff; then mark as DISCOVERED for later |
| Disk full (raw storage) | Alert admin; pause ingestion |

---

## Configuration

```yaml
domain: knowledge_acquisition
engines:
  ingestion:
    sources: ...       # See engines/ingestion-engine.md
  code_intelligence:
    languages: [python, typescript, java]
    max_file_size_mb: 5
  extraction:
    llm:
      model: gpt-4o-mini
      max_tokens: 4096
    rules:
      adr_pattern: "ADR\\s*-?\\s*\\d+"
      requirement_pattern: "^(As a|Given|When|Then)"
```