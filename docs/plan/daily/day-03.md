# Day 3 — Git Connector (Phase 1)

> **Phase:** 1 — Ingestion Engine | **Date:** Day 3 of 45 | **Goal:** Build GitSourceConnector for cloning, pulling, and tracking changes

---

## 🎯 Daily Target

**Deliverable:** Working Git connector that normalizes repo data into KnowledgeObjects

---

## ✅ Tasks

### 1. Base Connector Interface (`engines/ingestion/connectors.py`)
- [ ] `SourceConnector` ABC with methods:
  - `connect() -> None`
  - `disconnect() -> None`
  - `list_files() -> list[FileInfo]`
  - `get_file(path: str) -> FileContent`
  - `get_changes(since: datetime) -> list[Change]`
  - `normalize(file_info: FileInfo) -> list[KnowledgeObject]`

### 2. Git Data Models
- [ ] `GitFileInfo`: path, size, hash, mode, last_commit
- [ ] `GitFileContent`: path, content, encoding, language
- [ ] `GitChange`: path, change_type (ADDED/MODIFIED/DELETED), old_hash, new_hash, commit_info

### 3. Implement GitSourceConnector
- [ ] Constructor: `repo_url`, `branch`, `auth` (ssh/token/basic), `local_path`
- [ ] `connect()`: clone if not exists, else pull latest
- [ ] `list_files()`: use `git ls-files` for tracked files
- [ ] `get_file()`: read file content, detect language from extension
- [ ] `get_changes(since)`: `git log --since --name-status` for incremental sync
- [ ] Auth support:
  - SSH: use SSH agent / key file
  - Token: HTTPS with token in URL
  - Basic: username/password
- [ ] Handle large repos: shallow clone option, sparse checkout

### 4. Normalize Git Data → KnowledgeObjects
- [ ] Repository entity: `EntityType.REPOSITORY`
- [ ] Module entity: `EntityType.MODULE` (top-level directories)
- [ ] File entity: `EntityType.FILE` with language, size, hash
- [ ] SourceReference: `SourceType.GIT`, commit SHA as `source_id`
- [ ] Relationships: `CONTAINS` (repo→module→file)

### 5. Unit Tests (`tests/unit/test_git_connector.py`)
- [ ] Mock git commands, test clone/pull logic
- [ ] Test file listing and content retrieval
- [ ] Test change detection with mocked git log
- [ ] Test normalization output structure
- [ ] Test auth variations

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Clones repo via SSH/token/basic auth | ☐ |
| Lists all tracked files with metadata | ☐ |
| Reads file content with language detection | ☐ |
| Detects changes since timestamp (incremental) | ☐ |
| Normalizes to KnowledgeObjects (REPOSITORY, MODULE, FILE) | ☐ |
| Creates CONTAINS relationships | ☐ |
| SourceReference has correct GIT type and commit SHA | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 4 (Confluence connector), Day 6 (SyncManager needs all connectors)
- **Blocked by:** Day 2 (KnowledgeObject, SourceReference, Config)

---

## 📝 Notes

- Use `gitpython` or subprocess for git operations
- Handle git errors gracefully (network, auth, conflicts)
- Shallow clone (`--depth=1`) for speed, full history for change detection
- File language detection: use `pygments` or extension mapping
- Commit: `feat: git connector with clone, pull, change detection, normalization`