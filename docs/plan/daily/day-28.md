# Day 28 — REST API (Phase 7)

> **Phase:** 7 — CLI, API & Integration | **Date:** Day 28 of 30 | **Goal:** Build FastAPI app with endpoints and RBAC auth middleware

---

## 🎯 Daily Target

**Deliverable:** REST API with 10+ endpoints, OpenAPI spec, and role-based access control

---

## ✅ Tasks

### 1. FastAPI App (`api/main.py`)
- [ ] Initialize FastAPI app with title, description, version
- [ ] Include routers for ingest, query, context, graph, sources, health, audit
- [ ] Add CORS middleware
- [ ] Add exception handlers

### 2. Endpoints
- [ ] `POST /ingest` — trigger ingestion with source list
- [ ] `GET /ingest/status` — check ingestion progress
- [ ] `POST /query` — natural language query
- [ ] `POST /context` — get context package
- [ ] `GET /knowledge/{id}` — get knowledge object with traceability
- [ ] `GET /graph/explore` — explore knowledge graph (BFS/DFS)
- [ ] `GET /sources/status` — check source sync status
- [ ] `GET /health` — health check with component status
- [ ] `GET /audit` — audit log (requires ADMIN/ARCHITECT)
- [ ] `GET /openapi.json` — auto-generated OpenAPI spec
- [ ] `GET /docs` — Swagger UI

### 3. Auth Middleware (`api/auth.py`)
- [ ] JWT/OAuth2 token validation
- [ ] Role-based access control:
  - **ADMIN**: full access
  - **ARCHITECT**: read all, trigger re-extraction, view audit
  - **DEVELOPER**: read own projects, run ingestion
  - **VIEWER**: read-only public knowledge
  - **SERVICE**: programmatic access, scoped
- [ ] Dependency injection for auth in endpoints
- [ ] Public endpoints (health, openapi) without auth

### 4. Request/Response Validation
- [ ] Pydantic models for all request/response bodies
- [ ] Validation error handling with 422 responses
- [ ] Example responses in OpenAPI

### 5. Unit & Integration Tests (`tests/integration/test_api.py`)
- [ ] Test all endpoints with mock authentication
- [ ] Test RBAC enforcement
- [ ] Test error responses
- [ ] Test OpenAPI spec generation
- [ ] Test health check endpoint

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| All 10+ endpoints implemented | ☐ |
| OpenAPI spec generated and accessible | ☐ |
| RBAC middleware enforces roles correctly | ☐ |
| Request/response validation works | ☐ |
| Health check returns component status | ☐ |
| Integration tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 29 (E2E integration), Phase 8 (Evaluation)
- **Blocked by:** Day 27 (CLI), Phase 1-6 (engines)

---

## 📝 Notes

- Use `fastapi` and `uvicorn` (already in requirements)
- JWT validation using `python-jose` and `passlib`
- Store OpenAPI spec in `openapi.yaml` version
- Commit: `feat: REST API with endpoints, auth middleware, and OpenAPI spec`