# Engine 1: Ingestion Engine

> Execution Capability: Connect, sync, and normalize raw data from sources.
> [[glossary]]

---

## Role

Convert raw project data from multiple sources into a normalized, consistent format ready for downstream processing. This is the entry point of the entire pipeline.

---

## Sources

| Source | Connector | Sync Mode | Data Type | Auth |
|--------|-----------|-----------|-----------|------|
| Git Repository | `GitSourceConnector` | Push event (webhook) / Schedule (polling) | Code files, commits, branches, tags | SSH key, token, username/password |
| Confluence | `ConfluenceSourceConnector` | Webhook / Schedule (hourly) | Pages, comments, attachments, labels | OAuth2 / API token |
| Jira | `JiraSourceConnector` | Webhook / Schedule (every 15min) | Issues, fields, comments, transitions, attachments | OAuth2 / API token |
| Documents | `DocumentSourceConnector` | File watcher / On-change | Markdown, PDF (text), HTML, OpenAPI, DB schema | None (local) / HTTP auth |
| API Specs | `ApiSpecConnector` | Schedule (daily) | OpenAPI 3.x, GraphQL schema, Protobuf | As configured per spec source |

---

## Connector Interface

Every connector implements this interface:

```python
class SourceConnector(Protocol):
    """Interface that all source connectors must implement."""
    
    source_type: SourceType
    
    async def connect(self) -> None:
        """Establish connection to source."""
        ...
    
    async def disconnect(self) -> None:
        """Close connection."""
        ...
    
    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        """List all items (paginated)."""
        ...
    
    async def get_item(self, item_id: str) -> RawItem:
        """Get a single item by ID."""
        ...
    
    async def detect_changes(self, since: datetime) -> list[RawItem]:
        """Detect changes since last sync."""
        ...
    
    def health_check(self) -> bool:
        """Check if connector is healthy."""
        ...
```

```python
class RawItem(BaseModel):
    """Normalized raw data from any source."""
    
    item_id: str                           # Unique ID within source
    source_type: SourceType
    title: str
    content: str                           # Plain text representation
    content_type: str                      # markdown | text | json | xml
    metadata: dict[str, Any]               # Source-specific metadata
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = []
```

---

## Capabilities

| Capability | Description | Implementation |
|------------|-------------|----------------|
| **Connectors** | Pluggable connectors for each source type | Strategy pattern; register via config |
| **Incremental Sync** | Only fetch changed data since last sync | Content hash comparison + source timestamps |
| **Webhooks** | Real-time change detection | HTTP listener; event queue for async processing |
| **Change Detection** | Diff-based: what changed since last ingestion | SHA-256 of content; compare with stored hashes |
| **Version Tracking** | Know which version of source is indexed | Store `last_synced` + `content_hash` per source |
| **Normalization** | Convert all sources to common `RawItem` format | Per-connector normalize() method |
| **Rate Limiting** | Respect source API rate limits | Token bucket per connector; exponential backoff |
| **Retry Logic** | Handle transient failures gracefully | 3 retries with exponential backoff |

---

## Sync Manager

Orchestrates all connectors:

```python
class SyncManager:
    """Orchestrates incremental sync across all connectors."""
    
    async def run_full_sync(self) -> SyncResult:
        """Sync all configured sources from scratch."""
        ...
    
    async def run_incremental_sync(self) -> SyncResult:
        """Sync only changed data since last sync."""
        ...
    
    async def sync_source(self, source_config: SourceConfig) -> SourceSyncResult:
        """Sync a single source."""
        ...
    
    def schedule(self, cron_expr: str) -> None:
        """Set up periodic sync schedule."""
        ...
```

**SyncResult:**
```python
class SyncResult(BaseModel):
    total_items_processed: int
    new_items: int
    updated_items: int
    deleted_items: int
    errors: list[SyncError]
    duration_seconds: float
```

---

## Output

Normalized raw data objects with lifecycle_state = `DISCOVERED`:

```python
# Output of Ingestion Engine -> input to Code Intelligence / Extraction
class IngestionOutput(BaseModel):
    raw_items: list[RawItem]
    source_manifest: dict[str, SourceManifest]
    sync_metadata: SyncMetadata
```

```python
class SourceManifest(BaseModel):
    source_type: SourceType
    source_id: str
    last_synced: datetime
    total_items: int
    content_hash: str        # Hash of all items for change detection
```

---

## Configuration Schema

```yaml
ingestion:
  sources:
    git:
      repos:
        - url: https://github.com/org/project
          branch: main
          sync_interval: 5m
          auth:
            type: token
            token_ref: secrets.GIT_TOKEN
          include_paths:
            - "**/*.py"
            - "**/*.ts"
            - "**/openapi.yaml"
          exclude_paths:
            - "**/test_*.py"
            - "**/*.test.ts"
            - "**/__pycache__/**"
    
    confluence:
      base_url: https://org.atlassian.net
      spaces: [ARCH, DOCS]
      sync_interval: 1h
      auth:
        type: oauth2
      include_types: [page, blogpost]
      exclude_labels: [draft, internal-only]
    
    jira:
      base_url: https://org.atlassian.net
      projects: [PROJ]
      sync_interval: 15m
      auth:
        type: oauth2
      issue_types: [Bug, Story, Task, Epic]
      include_statuses: [Open, In Progress, Done]
    
    documents:
      paths:
        - local: ./docs
        - url: https://example.com/specs
      sync_interval: 1h
      supported_formats: [md, pdf, yaml, json]
  
  sync:
    max_concurrent: 3
    retry_attempts: 3
    retry_backoff: exponential
    rate_limit_per_source: 60  # requests per minute
```

---

## CLI Commands

```bash
# Full sync of all sources
pkh ingest --sync

# Incremental sync (only changes)
pkh ingest --sync --incremental

# Sync specific source
pkh ingest --source git://github.com/org/project
pkh ingest --source confluence://ARCH
pkh ingest --source jira://PROJ

# List configured sources and their status
pkh ingest --list

# View last sync result
pkh ingest --status
```