# Day 27 — CLI Interface (Phase 7)

> **Phase:** 7 — CLI, API & Integration | **Date:** Day 27 of 30 | **Goal:** Build full CLI interface with all commands

---

## 🎯 Daily Target

**Deliverable:** Complete CLI with 8 commands for end-to-end PKH operations

---

## ✅ Tasks

### 1. CLI Commands (`cli/main.py`)
- [ ] `pkh init` — scaffold project config with all sections
- [ ] `pkh ingest` — full ingestion pipeline with progress tracking
- [ ] `pkh query "question"` — natural language query with intent display
- [ ] `pkh context --query "..."` — raw context package for AI agents
- [ ] `pkh graph --entity "Name"` — visualize knowledge graph (ASCII/JSON)
- [ ] `pkh sync` — incremental sync with change report
- [ ] `pkh status` — ingestion status, counts, freshness, governance violations
- [ ] `pkh audit` — view audit log (ADMIN/ARCHITECT role required)

### 2. Output Formatting
- [ ] Rich tables for status, knowledge objects, relationships
- [ ] JSON output for programmatic use (`--json` flag)
- [ ] ASCII graph visualization
- [ ] Color-coded lifecycle states
- [ ] Progress bars for long operations

### 3. Integration with Engines
- [ ] Wire CLI to ingestion engine
- [ ] Wire CLI to retrieval engine
- [ ] Wire CLI to context delivery engine
- [ ] Wire CLI to storage engine

### 4. Error Handling & UX
- [ ] Clear error messages with suggestions
- [ ] Exit codes: 0=success, 1=general error, 2=config error, 3=auth error
- [ ] Verbose mode (`-v`, `-vv`) for debugging
- [ ] Help text with examples for each command

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| All 8 commands implemented and functional | ☐ |
| Rich output formatting works | ☐ |
| JSON output for programmatic use | ☐ |
| Progress tracking for ingestion/sync | ☐ |
| Error messages are clear and actionable | ☐ |
| Help text includes examples | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 28 (API), Day 29 (E2E integration)
- **Blocked by:** Phase 1-6 (all engines complete)

---

## 📝 Notes

- Use `typer` for CLI framework
- Use `rich` for tables, progress bars, trees
- Make CLI entry point: `pkh` command
- Commit: `feat: complete CLI interface with all commands`