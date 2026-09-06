# Day 6 — Document Connector & SyncManager (Phase 1)

> **Phase:** 1 — Ingestion Engine | **Date:** Day 6 of 45 | **Goal:** Build DocumentSourceConnector; implement SyncManager + ChangeDetector

---

## 🎯 Daily Target

**Deliverable:** Document connector for local/URL docs + SyncManager orchestrating all connectors with incremental sync

---

## ✅ Tasks

### 1. Document Data Models
- [ ] `DocumentInfo`: path, size, last_modified, mime_type, source_type (LOCAL/URL)
- [ ] `DocumentContent`: path, content, format (markdown/pdf/txt/yaml/json), title
- [ ] `DocumentChange`: path, change_type (ADDED/MODIFIED/DELETED), last_modified

### 2. Implement DocumentSourceConnector
- [ ] Constructor: `paths` (list), `patterns` (glob, e.g., `*.md`, `*.pdf`, `*.yaml`), `follow_symlinks`
- [ ] `connect()`: validate paths exist, create watchers
- [ ] `list_files()`: walk directories, apply glob patterns, detect file types
- [ ] `get_file()`: read file content
  - Markdown: read directly
  - PDF: `pdfplumber` or `PyPDF2` for text extraction
  - YAML/JSON: parse to dict
  - OpenAPI: parse spec → ENDPOINT entities
  - DB schema files: parse to TABLE/INDEX entities
- [ ] `get_changes(since)`: compare file modification times or content hashes
- [ ] URL-based docs: fetch via HTTP, cache locally

### 3. Normalize → KnowledgeObjects
- [ ] Document: `EntityType.DOCUMENT` (markdown, text, PDF)
- [ ] APISpec: `EntityType.API_SPEC` (OpenAPI files)
- [ ] Endpoint: `EntityType.ENDPOINT` (paths from OpenAPI)
- [ ] Table: `EntityType.TABLE` (database schema columns)
- [ ] SourceReference: `SourceType.DOCUMENT`, file path as `source_id`

### 4. Implement SyncManager (`sync_manager.py`)
- [ ] Constructor: `config` (all source configs), `metadata_db` (track sync state)
- [ ] `run_full_sync()`: call all connectors, full ingestion
- [ ] `run_incremental_sync(since)`: call all connectors with change detection
- [ ] Track sync state in metadata:
  - `sources` table: source_id, type, last_sync_timestamp, status, error
  - `files` table: file_id, source_id, path, hash, last_modified
- [ ] Parallel ingestion: use `asyncio.gather` for multiple sources
- [ ] Error handling: one source fails, others continue

### 5. Implement ChangeDetector (`change_detector.py`)
- [ ] `get_new_files(source_id)` → unchanged files since last sync
- [ ] `get_modified_files(source_id)` → files changed since last sync
- [ ] `get_deleted_files(source_id)` → files removed since last sync
- [ ] Hash-based change detection (content hash, not just mtime)
- [ ] `update_sync_state(source_id, files)` → persist new sync state

### 6. Webhook Listener (Stub)
- [ ] `WebhookServer` class on configurable port (e.g., 8080)
- [ ] Endpoints: `/webhook/git` (GitHub/GitLab push), `/webhook/confluence` (page update), `/webhook/jira` (issue transition)
- [ ] Verify webhook signatures (GitHub HMAC-SHA256)
- [ ] Queue webhook events for async processing

### 7. Unit Tests (`tests/unit/test_document_connector.py`, `tests/unit/test_sync_manager.py`)
- [ ] Mock filesystem operations, test file listing
- [ ] Test PDF parsing (mock or real sample)
- [ ] Test sync state tracking
- [ ] Test incremental sync detects new/modified/deleted files
- [ ] Test SyncManager orchestrates multiple connectors

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Fetches docs from local filesystem with glob patterns | ☐ |
| Parses PDF, YAML, OpenAPI, DB schema correctly | ☐ |
| Normalizes to correct entity types (DOCUMENT, API_SPEC, ENDPOINT, TABLE) | ☐ |
| SyncManager runs full + incremental sync across all sources | ☐ |
| ChangeDetector uses content hash for diff-based sync | ☐ |
| Sync state tracked in metadata DB | ☐ |
| Webhook server stub with endpoints | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 7 (CLI), Day 9 (Extraction engine consumes synced data)
- **Blocked by:** Day 2 (Config), Day 3-5 (all connectors)

---

## 📝 Notes

- Use `watchdog` for filesystem watching in webhook mode
- Content hash: `hashlib.sha256(content.encode()).hexdigest()`
- Sync state: SQLite table `sync_state(source_id, file_path, file_hash, last_synced)`
- Parallel connectors: async/await, timeout per source (e.g., 300s)
- Commit: `feat: document connector, sync manager, change detector`