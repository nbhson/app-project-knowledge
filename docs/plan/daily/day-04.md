# Day 4 — Confluence Connector (Phase 1)

> **Phase:** 1 — Ingestion Engine | **Date:** Day 4 of 30 | **Goal:** Build ConfluenceSourceConnector for fetching pages, parsing content, detecting ADRs/specs

---

## 🎯 Daily Target

**Deliverable:** Working Confluence connector that normalizes pages into KnowledgeObjects

---

## ✅ Tasks

### 1. Confluence Data Models
- [ ] `ConfluencePageInfo`: id, title, space_key, version, url, last_modified, parent_id
- [ ] `ConfluencePageContent`: id, title, body (storage format), body_markdown, labels
- [ ] `ConfluenceSpace`: key, name, type, homepage_id

### 2. Implement ConfluenceSourceConnector
- [ ] Constructor: `base_url`, `spaces`, `auth` (bearer token/basic), `page_patterns`
- [ ] `connect()`: validate credentials, test API access
- [ ] `list_files()` → `list_pages()`: fetch all pages in configured spaces (paginated)
- [ ] `get_file()` → `get_page(page_id)`: fetch page content + metadata
- [ ] `get_changes(since)`: use Confluence REST API `expand=version` + filter by `version.when`
- [ ] Auth: Bearer token (PAT), Basic auth (email + API token)

### 3. Parse Confluence Storage Format → Markdown
- [ ] Use `confluence2markdown` or custom parser for storage format (XHTML-based)
- [ ] Handle: headings, lists, tables, code blocks, macros (info, warning, note, panel)
- [ ] Extract macro content: `ac:structured-macro` → markdown equivalents
- [ ] Preserve links: `[text|url]` → `[text](url)`

### 4. Detect Special Document Types
- [ ] ADR detection: title pattern `ADR-*`, `Architecture Decision*`, or labels `adr`, `architecture-decision`
- [ ] Design doc detection: labels `design`, `spec`, `architecture`
- [ ] API spec detection: labels `api`, `openapi`, `swagger` + content patterns
- [ ] Requirement detection: labels `requirement`, `req` + structured content

### 5. Normalize → KnowledgeObjects
- [ ] Document entity: `EntityType.DOCUMENT` (general pages)
- [ ] ArchitectureDecision entity: `EntityType.ADR` (detected ADRs)
- [ ] Requirement entity: `EntityType.REQUIREMENT` (detected requirements)
- [ ] APISpec entity: `EntityType.API_SPEC` (detected specs)
- [ ] Endpoint entity: `EntityType.ENDPOINT` (from API specs)
- [ ] SourceReference: `SourceType.CONFLUENCE`, page ID as `source_id`, version for change tracking
- [ ] Relationships: `CONTAINS` (space→page), `DOCUMENTS` (ADR→related entities)

### 6. Unit Tests (`tests/unit/test_confluence_connector.py`)
- [ ] Mock Confluence REST API responses
- [ ] Test page listing with pagination
- [ ] Test storage format → markdown conversion
- [ ] Test ADR/design doc detection
- [ ] Test normalization to correct entity types

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Fetches pages from configured spaces | ☐ |
| Parses storage format to markdown | ☐ |
| Detects ADRs by title/label pattern | ☐ |
| Detects design docs, API specs, requirements | ☐ |
| Normalizes to correct entity types (DOCUMENT, ADR, REQUIREMENT, API_SPEC, ENDPOINT) | ☐ |
| Tracks page versions for change detection | ☐ |
| SourceReference has CONFLUENCE type and page ID | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 6 (SyncManager needs all connectors)
- **Blocked by:** Day 2 (KnowledgeObject, Config), Day 3 (Base connector interface)

---

## 📝 Notes

- Use `atlassian-python-api` or `httpx` for REST calls
- Confluence Cloud vs Server/DC API differences (handle both)
- Rate limiting: respect `Retry-After` headers
- Large spaces: use `cql` queries for efficient filtering
- Commit: `feat: confluence connector with page fetch, parsing, ADR detection`