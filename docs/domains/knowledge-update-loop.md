# Knowledge Update Loop Domain

> Cross-cutting: Keep knowledge fresh and accurate over time.

---

## Responsibility

Ensure the Knowledge Core stays synchronized with its sources. Knowledge decays without updates -- stale knowledge leads to wrong answers. This domain monitors source changes and triggers re-processing when needed.

---

## Update Triggers

| Trigger | Frequency | Source | Action |
|---------|-----------|--------|--------|
| Git push | Real-time (webhook) | Engine 1 - Git Connector | Queue file for re-ingestion |
| Confluence page edit | Real-time (webhook) | Engine 1 - Confluence Connector | Queue page for re-extraction |
| Jira issue update | Real-time (webhook) | Engine 1 - Jira Connector | Queue issue for re-processing |
| Scheduled full sync | Daily / Hourly | Engine 1 - SyncManager | Full re-sync of all sources |
| Source deletion detected | On detect | Engine 1 - ChangeDetector | Mark knowledge SUPERSEDED |
| Staleness threshold | Continuous monitor | This domain | Flag or prompt re-sync |

---

## Update Flow

```
New Data Detected (webhook or scheduled)
         |
         v
+---------------------------+
|  Change Detection         |  Diff against last known state
|                             |  - Content hash comparison
|  - What changed?          |  - New/modified/deleted items
|  - What is new?           |
+---------------------------+
         |
         v
+---------------------------+
|  Re-Extraction (if changed)|  Only re-process items that changed
|                             |  - New items: DISCOVERED -> EXTRACTED
|  - Same content?          |  - Updated items: ACTIVE -> UPDATED
|  -> No change: skip       |  - Deleted items: ACTIVE -> SUPERSEDED
+---------------------------+
         |
         v
+---------------------------+
|  Lifecycle Update         |  Apply state transitions
|                             |
|  Same content -> No change |
|  Updated content ->        |
|    UPDATED state ->        |
|    Re-validate -> ACTIVE   |
|  Removed source ->         |
|    SUPERSEDED ->           |
|    DEPRECATED ->           |
|    ARCHIVED (after hold)   |
+---------------------------+
         |
         v
+---------------------------+
|  Knowledge Core Updated   |  Persist state changes to all layers
+---------------------------+
         |
         v
+---------------------------+
|  Notification             |  Alert relevant stakeholders
|                             |  - Slack/Teams webhook
|  - Who cares?             |  - Email for critical changes
|  - Send digest            |
+---------------------------+
```

---

## Staleness Detection

| Signal | Threshold | Action |
|--------|-----------|--------|
| Source not synced > 7 days | Warning | Flag KnowledgeObjects with staleness warning |
| Source not synced > 30 days | Warning + Prompt | Show "source may be stale" in results; prompt admin |
| Source deleted without notice | Critical | Mark all derived knowledge SUPERSEDED |
| New version of source detected | Info | Trigger re-extraction pipeline |
| Knowledge not queried > 180 days | Info | Suggest archiving (does not auto-archive) |

---

## Content Hash Strategy

To detect changes efficiently:

```python
class ChangeDetector:
    """Detects what changed between syncs."""
    
    async def compute_hash(self, source_type: str, source_id: str, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    async def detect_changes(self, source_config: SourceConfig) -> list[Change]:
        """Compare current source state against last known state."""
        current_items = await self._list_current_items(source_config)
        last_known = await self._get_last_known_hashes(source_config.source_type, source_config.source_id)
        
        changes = []
        for item in current_items:
            current_hash = await self.compute_hash(item.type, item.id, item.content)
            last_hash = last_known.get(item.id)
            
            if last_hash is None:
                changes.append(Change(type="NEW", item=item, hash=current_hash))
            elif last_hash != current_hash:
                changes.append(Change(type="UPDATED", item=item, 
                                      old_hash=last_hash, new_hash=current_hash))
        
        # Detect deletions
        for known_id, known_hash in last_known.items():
            if known_id not in {item.id for item in current_items}:
                changes.append(Change(type="DELETED", source_id=known_id, hash=known_hash))
        
        return changes
```

---

## Supersession Logic

When new knowledge replaces old knowledge:

```python
def determine_supersession(old: KnowledgeObject, new: KnowledgeObject) -> bool:
    """Determine if new knowledge supersedes old knowledge."""
    
    # Same source, same topic
    if old.source_references[0].source_id != new.source_references[0].source_id:
        return False
    
    # Same entity type and name
    if old.properties.get("name") != new.properties.get("name"):
        return False
    
    # New has higher confidence
    if new.confidence <= old.confidence:
        return False
    
    # New is more recent
    if new.updated_at <= old.updated_at:
        return False
    
    return True
```

---

## Configuration

```yaml
update_loop:
  polling:
    interval: 5m              # How often to check for changes
    full_sync_interval: 24h   # Full re-sync every 24 hours
  
  staleness:
    warning_days: 7
    prompt_days: 30
    archive_suggest_days: 180
  
  supersession:
    min_confidence_delta: 0.1  # New must be this much more confident
    require_recency: true      # New must be more recent
  
  notifications:
    slack_webhook: ""
    email_admins: false
    digest_frequency: daily
```