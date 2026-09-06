# Day 5 — Jira Connector (Phase 1)

> **Phase:** 1 — Ingestion Engine | **Date:** Day 5 of 45 | **Goal:** Build JiraSourceConnector for fetching issues, building requirement hierarchy

---

## 🎯 Daily Target

**Deliverable:** Working Jira connector that normalizes issues into KnowledgeObjects with Epic→Story→Task hierarchy

---

## ✅ Tasks

### 1. Jira Data Models
- [ ] `JiraIssueInfo`: id, key, project_key, issue_type, status, priority, assignee, story_points, labels, created, updated
- [ ] `JiraIssueContent`: id, key, summary, description, acceptance_criteria, comments, transitions, fields

### 2. Implement JiraSourceConnector
- [ ] Constructor: `base_url`, `projects`, `auth` (email+token/basic/oauth), `issue_types` (epic, story, task, bug)
- [ ] `connect()`: validate credentials, test API access
- [ ] `list_files()` → `list_issues()`: fetch issues by project key, filter by types
- [ ] `get_file()` → `get_issue(key)`: fetch full issue with all fields
- [ ] `get_changes(since)`: use JQL `updatedDate >= startOfDay(-N)` or `changelog` API
- [ ] Auth: email + API token (Cloud), basic auth (Server), OAuth2 (enterprise)

### 3. Build Requirement Hierarchy
- [ ] Parse issue fields:
  - `summary` → title
  - `description` → content (convert Jira wiki markup to markdown)
  - `acceptance_criteria` → structured content
  - `comments` → discussions (attach to KnowledgeObject)
  - `transitions` → lifecycle state history
- [ ] Build graph: Epic → Story → Task → Sub-task
  - Use `parent` field or `issuetype = Epic` + `issues` relationship
  - Detect `JIRA-123` references in descriptions/comments
- [ ] Map issue status → LifecycleState:
  - `To Do` → DISCOVERED
  - `In Progress` → EXTRACTED
  - `In Review` → VALIDATING
  - `Done` → ACTIVE
  - `Closed` → DEPRECATED
  - `Removed` → SUPERSEDED

### 4. Normalize → KnowledgeObjects
- [ ] Epic: `EntityType.EPIC`
- [ ] Story: `EntityType.STORY`
- [ ] Task: `EntityType.TASK`
- [ ] Bug: `EntityType.BUG`
- [ ] Requirement: `EntityType.REQUIREMENT` (mapped from user stories)
- [ ] SourceReference: `SourceType.JIRA`, issue key as `source_id`, project key
- [ ] Relationships:
  - `IMPLEMENTS` (Story → Feature)
  - `TRACES_TO` (Code → JIRA issue key)
  - `REQUIRES` (Epic → Story)
  - `PART_OF` (Task → Story)

### 5. Unit Tests (`tests/unit/test_jira_connector.py`)
- [ ] Mock Jira REST API responses
- [ ] Test issue listing with pagination
- [ ] Test hierarchy building (Epic→Story→Task)
- [ ] Test Jira wiki markup → markdown conversion
- [ ] Test normalization to correct entity types
- [ ] Test status → lifecycle state mapping

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Fetches issues from configured projects | ☐ |
| Parses summary, description, acceptance criteria | ☐ |
| Builds Epic→Story→Task hierarchy | ☐ |
| Maps Jira status → LifecycleState correctly | ☐ |
| Normalizes to correct entity types (EPIC, STORY, TASK, BUG, REQUIREMENT) | ☐ |
| Detects JIRA-XXX references in descriptions | ☐ |
| SourceReference has JIRA type and issue key | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 6 (SyncManager needs all connectors)
- **Blocked by:** Day 2 (KnowledgeObject, Config), Day 3 (Base connector interface)

---

## 📝 Notes

- Use `atlassian-python-api` or `httpx` for REST calls
- Jira Cloud vs Server/DC API differences (handle both)
- Jira wiki markup to markdown: handle `h1.`, `*bold*`, `_italic_`, `{code}`, tables
- Issue types vary by project (custom fields may differ)
- Commit: `feat: jira connector with issue fetch, hierarchy, status mapping`