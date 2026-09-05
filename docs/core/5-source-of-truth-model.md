# Source of Truth Model

> Principle 2: Source Traceability - Every knowledge must answer: Where did this come from?
> [[glossary]]

---

## The Traceability Chain

Every piece of information that flows through PKH carries its origin forward. The traceability chain is:

```
User Query
    |
    v
Context Package (what the LLM sees)
    |
    +-- knowledge[]: KnowledgeChunk[]
    |       |
    |       +-- each chunk has: id, type, content, confidence, lifecycle_state
    |       +-- each chunk links to: sources[]
    |
    +-- relationships[]: RelationshipChunk[]
    |       |
    |       +-- from, to, type
    |       +-- each links back to source KnowledgeObjects
    |
    +-- sources: SourceReference[] (deduplicated)
    |
    v
Knowledge Core (where everything is stored and queried)
    |
    +-- Vector Store: semantic similarity (embeddings)
    +-- Graph Store: relationship traversal (entities + edges)
    +-- Metadata Store: structured filtering (SQL queries)
    +-- Raw Sources: original data preservation (S3 / local)
    |
    v
Source of Truth (the original systems)
    +-- Git Repository (code, commits, branches)
    +-- Confluence (pages, ADRs, specs)
    +-- Jira (issues, epics, stories, tasks)
    +-- File System (local docs, OpenAPI specs)
```

---

## Source of Truth Mapping

| Knowledge Type | Source of Truth | Engine(s) Responsible | Confidence Baseline |
|----------------|-----------------|----------------------|---------------------|
| Code implementation | Git Repository (commit, branch, file) | 2. Code Intelligence | 1.0 (direct source) |
| Requirement | Jira Issue | 1. Ingestion | 1.0 (direct source) |
| Architecture decision | Confluence ADR page | 1. Ingestion + 3. Extraction | 0.9 (extracted structure) |
| API Contract | OpenAPI spec file or code | 1. Ingestion | 1.0 (direct source) |
| Deployment config | Infrastructure repo / CI config | 1. Ingestion | 0.8 (structured parsing) |
| Business rule | Confluence doc or Jira | 3. Extraction | 0.7 (LLM-assisted) |
| Document | Confluence page or local file | 1. Ingestion | 1.0 (direct source) |
| Dependency | Code import / package manifest | 2. Code Intelligence | 1.0 (structural) |
| Call relationship | AST call expressions | 2. Code Intelligence | 0.95 (structural) |
| Requirement implementation link | Cross-reference analysis | 3. Extraction | 0.6 (inferred) |

---

## SourceReference Model

Every KnowledgeObject carries SourceReferences:

```python
class SourceReference(BaseModel):
    """Traceability link back to the original source."""
    
    source_type: SourceType              # GIT | CONFLUENCE | JIRA | DOCUMENT | API_SPEC
    source_id: str                       # commit hash, page ID, issue key, etc.
    url: str = ""                        # direct link to source
    title: str = ""                      # title of source
    last_synced: datetime                # when last synced
    extra: dict[str, Any] = {}           # additional metadata
```

**Source type specifics:**

| SourceType | source_id format | url format | extra keys |
|------------|------------------|------------|------------|
| `GIT` | commit hash (40 hex chars) | `https://github.com/owner/repo/commit/<hash>` | `branch`, `file_path`, `line_start`, `line_end`, `blob_url` |
| `CONFLUENCE` | page ID (numeric string) | `https://org.atlassian.net/wiki/page/<id>/<title>` | `space_key`, `version`, `content_type`, `ancestor_ids` |
| `JIRA` | issue key (e.g., `PROJ-123`) | `https://org.atlassian.net/browse/<key>` | `issue_type`, `field_name`, `status`, `assignee` |
| `DOCUMENT` | file path relative to repo root | N/A (local reference) | `format`, `encoding`, `size_bytes`, `md5_hash` |
| `API_SPEC` | spec file path + endpoint path | N/A | `method`, `path`, `spec_version`, `schema_name` |

---

## Trust Boundary

```mermaid
graph TD
    T[TRUSTED ZONE\nSources Git/Confluence/Jira — 100% trusted\n"The source IS the truth"] -->|extraction introduces uncertainty| U[UNTRUSTED ZONE (but still valuable)\nExtracted Knowledge scored 0.0–1.0\n"This is our BEST INTERPRETATION of the source"]
```

**Key rules:**
1. Source data is NEVER modified. Always stored as-is in Raw Sources layer.
2. Extracted knowledge is ALWAYS accompanied by its confidence score.
3. When a user asks "show me the source," PKH provides the direct link.
4. When confidence is low (< 0.5), the context includes a warning flag.

---

## Conflict Resolution

When sources conflict (e.g., Confluence says X, but Jira says Y):

1. **Code always wins over docs** -- if Git and Confluence disagree about implementation, Git is authoritative.
2. **Newer always wins over older** -- if two ADRs exist, the one with later `last_synced` is preferred.
3. **Structured always wins over free-text** -- if Jira has structured fields, they override prose descriptions.
4. **Higher confidence wins** -- when extraction confidence differs, the higher-scored knowledge is surfaced.
5. **User override** -- humans can mark knowledge as authoritative regardless of above rules.