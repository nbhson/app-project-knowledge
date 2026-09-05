# Day 7 — Ingestion CLI and Integration Tests (Phase 1)

> **Phase:** 1 — Ingestion Engine | **Date:** Day 7 of 30 | **Goal:** Build CLI commands for ingestion and write integration tests

---

## 🎯 Daily Target

**Deliverable:** Working CLI commands for ingestion and comprehensive integration tests for all connectors

---

## ✅ Tasks

### 1. CLI Interface (`cli/main.py`)
- [ ] Implement `pkh ingest` command with multiple source flags:
  - `--source git://path` → Git connector
  - `--source confluence://SPACE` → Confluence connector
  - `--source jira://PROJECT` → Jira connector
  - `--source documents://path` → Document connector
  - `--sync` → Incremental sync (uses change_detector)
- [ ] Add progress tracking with progress bars (using `rich.progress`)
- [ ] Add logging with correlation IDs for traceability
- [ ] Support multiple sources in single command (comma-separated or repeated flags)
- [ ] CLI help text with clear usage examples

### 2. Integration Tests (`tests/integration/test_ingest.py`)
- [ ] Mock all connectors using `unittest.mock`:
  - Git: simulate clone/pull, file changes
  - Confluence: mock API responses for pages
  - Jira: mock issue data and transitions
  - Documents: mock file operations
- [ ] Test end-to-end workflow:
  - Ingest from multiple sources
  - Verify KnowledgeObjects created correctly
  - Check SourceReferences have correct metadata
  - Validate relationships (CONTAINS, TRACES_TO, etc.)
- [ ] Test incremental sync (`--sync`) with mocked changes
- [ ] Test error handling (connector failures, invalid sources)

### 3. Progress Tracking and Logging
- [ ] Add `rich.progress` progress bars for multi-source ingestion
- [ ] Implement structured logging with:
  - Correlation ID (per ingestion session)
  - Source-specific logs
  - Error/warning levels
  - JSON output format for container-friendly logging
- [ ] Log connector start/end times, file counts, errors

### 4. CLI Help and Documentation
- [ ] Add `--help` output with clear examples:
  - `pkh ingest --source git://project --source confluence://eng`
  - `pkh ingest --sync --source documents://docs`
- [ ] Add usage examples in README (to be written later)
- [ ] Ensure CLI exits with appropriate error codes

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `pkh ingest` supports multiple sources simultaneously | ☐ |
| Incremental sync (`--sync`) works with change detection | ☐ |
| Integration tests pass for all connectors (mocked) | ☐ |
| Progress bars show real-time status | ☐ |
| Structured JSON logging with correlation IDs | ☐ |
| CLI help text includes clear examples | ☐ |
| Tests cover success and error scenarios | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 6 (SyncManager, ChangeDetector), Day 8 (Extraction engine needs synced data)
- **Blocked by:** Day 2 (Config), Day 3-6 (all connectors)

---

## 📝 Notes

- Use `typer` for CLI implementation (already in requirements)
- Progress bars should show per-source status when multiple sources used
- Logging should include: session ID, timestamp, source name, status, error details
- Integration tests should use `pytest-asyncio` for async operations
- Commit: `feat: ingestion cli with multi-source support, integration tests, logging`