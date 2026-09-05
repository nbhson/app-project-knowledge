# Daily Implementation Plan

> **Project:** Project Knowledge Harness (PKH)
> **Total Days:** 45 (was 30 — +15 buffer for integration/hardening)
> **Goal:** Transform fragmented project information into a continuously evolving, connected, model-independent knowledge system

---

## 📋 Overview

This directory contains 45 daily implementation files, each with:
- 🎯 Clear daily target
- ✅ Actionable tasks
- 📋 Acceptance criteria
- 🔗 Dependencies (what blocks/blocked)
- 📝 Implementation notes
> **45-day note:** Day 1-30 giữ nguyên như 30-day plan; Day 31-45 là buffer mở rộng cho outbox/reconciler (Day 26-28), RRF tuning (Day 33-34), RBAC (Day 40-41), và hardening (Day 45). Xem `../plan.md` cho timeline mới.

---

## 🗓️ Day-by-Day Plan

| Day | Phase | Focus | File |
|-----|-------|-------|------|
| 1 | 0 — Foundation | Project Scaffolding | [day-01.md](day-01.md) |
| 2 | 0 — Foundation | Knowledge Model & Config | [day-02.md](day-02.md) |
| 3 | 1 — Ingestion | Git Connector | [day-03.md](day-03.md) |
| 4 | 1 — Ingestion | Confluence Connector | [day-04.md](day-04.md) |
| 5 | 1 — Ingestion | Jira Connector | [day-05.md](day-05.md) |
| 6 | 1 — Ingestion | Document Connector & SyncManager | [day-06.md](day-06.md) |
| 7 | 1 — Ingestion | Ingestion CLI & Integration Tests | [day-07.md](day-07.md) |
| 8 | 2 — Code Intelligence | AST Parser Foundation | [day-08.md](day-08.md) |
| 9 | 2 — Code Intelligence | Dependency & Call Graph | [day-09.md](day-09.md) |
| 10 | 2 — Code Intelligence | Code Knowledge Enrichment | [day-10.md](day-10.md) |
| 11 | 2 — Code Intelligence | Code Engine Tests & Integration | [day-11.md](day-11.md) |
| 12 | 3 — Extraction | Entity & Relationship Extraction | [day-12.md](day-12.md) |
| 13 | 3 — Extraction | LLM-Powered Extraction | [day-13.md](day-13.md) |
| 14 | 3 — Extraction | Decision & Rule Detection | [day-14.md](day-14.md) |
| 15 | 3 — Extraction | Extraction Pipeline & Validation | [day-15.md](day-15.md) |
| 16 | 4 — Storage | Metadata Store (SQLAlchemy) | [day-16.md](day-16.md) |
| 17 | 4 — Storage | Vector Store (ChromaDB) | [day-17.md](day-17.md) |
| 18 | 4 — Storage | Graph Store (NetworkX) | [day-18.md](day-18.md) |
| 19 | 4 — Storage | Storage Integration & Unified Queries | [day-19.md](day-19.md) |
| 20 | 5 — Retrieval | Intent Detection & Query Planning | [day-20.md](day-20.md) |
| 21 | 5 — Retrieval | Hybrid Retrieval (RRF) | [day-21.md](day-21.md) |
| 22 | 5 — Retrieval | Graph Traversal & Reranking | [day-22.md](day-22.md) |
| 23 | 5 — Retrieval | Retrieval Pipeline & Tests | [day-23.md](day-23.md) |
| 24 | 6 — Context Delivery | Context Assembly | [day-24.md](day-24.md) |
| 25 | 6 — Context Delivery | Model Adapters | [day-25.md](day-25.md) |
| 26 | 6 — Context Delivery | Context Contract & Streaming | [day-26.md](day-26.md) |
| 27 | 7 — CLI/API | CLI Interface | [day-27.md](day-27.md) |
| 28 | 7 — CLI/API | REST API | [day-28.md](day-28.md) |
| 29 | 7 — CLI/API | End-to-End Integration | [day-29.md](day-29.md) |
| 30 | 8 — Polish | Evaluation, Docs & Polish (part 1) | [day-30.md](day-30.md) |
| 31 | 5 — Retrieval | Hybrid Retrieval (RRF) — buffer | [day-31.md](day-31.md) |
| 32 | 5 — Retrieval | Graph Traversal & Reranking — buffer | [day-32.md](day-32.md) |
| 33 | 5 — Retrieval | Retrieval Pipeline & Golden Tests | [day-33.md](day-33.md) |
| 34 | 6 — Context | Context Assembly + Compressor | [day-34.md](day-34.md) |
| 35 | 6 — Context | Model Adapters | [day-35.md](day-35.md) |
| 36 | 6 — Context | Contract Validation & Caching | [day-36.md](day-36.md) |
| 37 | 7 — CLI/API | CLI Polish | [day-37.md](day-37.md) |
| 38 | 7 — CLI/API | REST API + RBAC | [day-38.md](day-38.md) |
| 39 | 7 — CLI/API | API Hardening & OpenAPI | [day-39.md](day-39.md) |
| 40 | 7 — CLI/API | E2E Integration — buffer | [day-40.md](day-40.md) |
| 41 | 8 — Polish | Evaluation Framework | [day-41.md](day-41.md) |
| 42 | 8 — Polish | Docs & Example Project | [day-42.md](day-42.md) |
| 43 | 8 — Polish | Docs Polish & Config Templates | [day-43.md](day-43.md) |
| 44 | 9 — Hardening | Bugfix & Coverage | [day-44.md](day-44.md) |
| 45 | 9 — Hardening | Load Test & Release Tag | [day-45.md](day-45.md) |

---

## 🏗️ Phases Summary

### Phase 0: Foundation (Day 1-3) — 45-day: +1 buffer
Project scaffold, Knowledge Model, Config system

### Phase 1: Ingestion Engine (Day 4-10) — 45-day: +2 buffer
Connect to Git, Confluence, Jira, Documents; detect changes; normalize

### Phase 2: Code Intelligence Engine (Day 11-15) — 45-day: +1 buffer
AST parsing, dependency analysis, call graphs, enrichment (Python-first)

### Phase 3: Knowledge Extraction Engine (Day 16-21) — 45-day: +2 buffer
Rule-based + LLM extraction, decision/rule detection, validation + calibration

### Phase 4: Knowledge Storage Engine (Day 22-28) — 45-day: +3 buffer (outbox/reconciler)
Metadata, Vector, Graph stores với outbox pattern, nightly check

### Phase 5: Retrieval Intelligence Engine (Day 29-34) — 45-day: +2 buffer
Intent classification, hybrid retrieval RRF, graph traversal, reranking

### Phase 6: Context Delivery Engine (Day 35-37) — 45-day: giữ nguyên
Context assembly, model adapters (Mock-first), validation, streaming

### Phase 7: CLI, API & Integration (Day 38-42) — 45-day: +2 buffer
Full CLI, REST API + RBAC, end-to-end pipeline

### Phase 8: Evaluation, Docs & Polish (Day 43-44) — 45-day: +1 buffer
Quality metrics, documentation, example project

### Phase 9: Hardening & Buffer (Day 45) — NEW in 45-day
Bugfix, coverage >80%, load test, release tag `v0.1.0`

---

## 📊 Progress Tracking

Use this checklist to track daily progress:

- [ ] Day 1 — Project Scaffolding
- [ ] Day 2 — Knowledge Model & Config
- [ ] Day 3 — Git Connector
- [ ] Day 4 — Confluence Connector
- [ ] Day 5 — Jira Connector
- [ ] Day 6 — Document Connector & SyncManager
- [ ] Day 7 — Ingestion CLI & Integration Tests
- [ ] Day 8 — AST Parser Foundation
- [ ] Day 9 — Dependency & Call Graph
- [ ] Day 10 — Code Knowledge Enrichment
- [ ] Day 11 — Code Engine Tests & Integration
- [ ] Day 12 — Entity & Relationship Extraction
- [ ] Day 13 — LLM-Powered Extraction
- [ ] Day 14 — Decision & Rule Detection
- [ ] Day 15 — Extraction Pipeline & Validation
- [ ] Day 16 — Metadata Store
- [ ] Day 17 — Vector Store
- [ ] Day 18 — Graph Store
- [ ] Day 19 — Storage Integration & Unified Queries
- [ ] Day 20 — Intent Detection & Query Planning
- [ ] Day 21 — Hybrid Retrieval
- [ ] Day 22 — Graph Traversal & Reranking
- [ ] Day 23 — Retrieval Pipeline & Tests
- [ ] Day 24 — Context Assembly
- [ ] Day 25 — Model Adapters
- [ ] Day 26 — Context Contract & Streaming
- [ ] Day 27 — CLI Interface
- [ ] Day 28 — REST API
- [ ] Day 29 — End-to-End Integration
- [ ] Day 30 — Evaluation, Docs & Polish (part 1)
- [ ] Day 31 — Hybrid Retrieval (buffer)
- [ ] Day 32 — Graph Traversal & Reranking (buffer)
- [ ] Day 33 — Retrieval Pipeline & Golden Tests
- [ ] Day 34 — Context Assembly + Compressor
- [ ] Day 35 — Model Adapters
- [ ] Day 36 — Contract Validation & Caching
- [ ] Day 37 — CLI Polish
- [ ] Day 38 — REST API + RBAC
- [ ] Day 39 — API Hardening & OpenAPI
- [ ] Day 40 — E2E Integration (buffer)
- [ ] Day 41 — Evaluation Framework
- [ ] Day 42 — Docs & Example Project
- [ ] Day 43 — Docs Polish & Config Templates
- [ ] Day 44 — Bugfix & Coverage
- [ ] Day 45 — Load Test & Release Tag

---

## 🔗 Related Documentation

- [Overall Plan](../plan.md) — Master implementation plan
- [Vision & Principles](../../core/1-vision-and-design-principles.md) — Core vision
- [Architecture](../../core/2-architecture.md) — System architecture
- [Knowledge Model](../../core/3-knowledge-model.md) — Knowledge structures
- [Glossary](../../glossary.md) — Term definitions

---

## 📝 Usage

For each day:
1. Read the day's file
2. Complete the tasks in order
3. Verify acceptance criteria
4. Run tests
5. Commit changes
6. Move to next day

Use git tags or branches to track daily progress:
```bash
git tag -a day-01-complete -m "Day 1: Project scaffolding complete"
```
