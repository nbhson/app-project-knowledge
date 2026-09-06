# PKH — Fix Plan (Toàn Diện)

> **Mục đích:** Đóng mọi gap P0/P1/P2 phát hiện trong audit code+docs ngày 06/09/2026. Fix xong thì `PYTHONPATH=src pytest` ≥45 tests, `ruff 0`, `mypy 0`, `ResourceWarning 0`, `vector restart` pass, `audit concurrent` pass, docs-code khớp.
> **Gốc:** `docs/plan/plan.md` (45-day), `docs/plan/daily/README.md`, `pyproject.toml:55`, `src/pkh/*` 4064 LOC.
> **Nguyên tắc:** Docs truth → P0 correctness/security → P1 completeness → P2 quality. Không làm song song task cùng chạm `src/pkh/storage/*`.

**Baseline hiện tại (06/09):** `pytest 36 passed, coverage 67.79%, ruff ~20 lỗi, mypy chưa chạy, .coverage tồn tại, src/pkh đã có` — trái với banner `no src yet` ở `README.md:5`/`CLAUDE.md:9`.

---

## 0. Tổng quan & Thứ tự

```
Phase 0 (Day 0, 0.5d)  Docs truth — unblock contributor
Phase 1 (Day 1-3)       P0 correctness/security — không ship được nếu thiếu
Phase 2 (Day 4-6)       P1 completeness — spec vs impl
Phase 3 (Day 7-8)       P2 quality — lint/type/coverage/polish
Gate mỗi phase: pytest + ruff + mypy theo scope phase (không claim done khi chỉ có docs).
```

**Gantt gọn:**

```
D0  [0.1-0.4] docs truth
D1  [1.1 vector] || [1.2 metadata] (khác file)
D2  [1.3 async] + [1.4 lifecycle] + [1.5 audit]
D3  [1.6 store leak] + [1.7 RBAC] — Gate P0
D4  [2.1 outbox] + [2.2 ingestion]
D5  [2.3 parser] + [2.4 extraction] + [2.5 retrieval]
D6  [2.6 context] + [2.7 adapter] — Gate P1
D7-8 [3.1-3.5] polish — Gate P2 + release tag
```

Tổng **~8 ngày** 1 người, **~4-5 ngày** nếu 2 người (chia storage vs engines).

---

## Phase 0 — Docs Truth (0.5 ngày) — Unblock

### 0.1 Sửa banner stale — P1
- **Files:** `README.md:5`, `CLAUDE.md:9`, `docs/project-structure.md:56`, `docs/overall-architecture.md:198`, `docs/deployment-guide.md:10`, `docs/plan/plan.md:12-15`
- **Làm:** Đổi `⚠️ Design-spec only — no src yet` → `✅ src exists (Phase 0-1 partial, scaffold 06/09) — verify: PYTHONPATH=src pytest --cov` + badge coverage thực `67.79%`. `project-structure.md:56` đổi `PLANNED NOT YET IMPLEMENTED` → `Implemented — see src/pkh/`. `plan.md:12` đổi `Current Status: Design Phase Only` → `Implementation In Progress (scaffold done, Phase 1-2 pending)`.
- **Verify:** `grep -r "no src yet" --exclude-dir=.git` = 0, `grep -rn "PLANNED, NOT YET" docs/` = 0.

### 0.2 Thống nhất taxonomy — P1 (critical)
- **Files:** `docs/core/3-knowledge-model.md:93`, `docs/glossary.md:81`, `docs/layers/knowledge-design.md:19`, `docs/plan/daily/day-01.md:81`, `src/pkh/models/knowledge.py:18`, `tests/unit/test_models.py:12`
- **Quyết:** Chọn `core/3` 23 entities làm truth. Quyết 1 tên: `API` vs `API_SPEC` (khuyến nghị giữ `API` theo glossary), `DECISION` vs `ADR` (giữ `DECISION`, `ADR` là subtype trong `properties`), giữ `BUSINESS_RULE`, xóa phantom `SUB_TASK`. Sync `knowledge.py:18` enum, `glossary:40` count, `layers/knowledge-design:19`, `day-01:81`. Thêm test cho mỗi `EntityType` trong `test_models.py`.
- **Verify:** `grep -rn "API_SPEC\|SUB_TASK" src/ docs/` chỉ còn 0 hoặc có comment `alias`.

### 0.3 Thống nhất SLO + MVP scope — P2
- **Files:** `docs/core/8-evaluation-framework.md:33`, `docs/layers/quality-and-trust.md:35`, `docs/plan/plan.md:675`, `docs/plan/plan.md:117` vs `docs/decisions/adr-005:32`, `docs/overall-architecture.md:197`
- **Quyết:** 1 SLO duy nhất: p99 retrieval `<1000ms` (lấy `core/8:33` làm gốc, sửa 2 nơi còn lại). MVP chốt `vector-only` theo `adr-005:32` (sửa `plan.md:117` từ `vector+keyword`). Sửa header `Day X of 30` → `45` trong `docs/plan/daily/day-*.md:3` + `overall-architecture.md:198` `Full (Day 8-30)` → `11-45`.
- **Verify:** `grep -rn "p99.*2000ms\|500ms for 10K" docs/` = 0 sau sửa.

### 0.4 Chốt consistency model — P1
- **Files:** `docs/domains/knowledge-core.md:67` vs `docs/engines/knowledge-storage-engine.md:177`, `src/pkh/storage/unified.py:27`, `src/pkh/storage/metadata.py:41`
- **Làm:** Sửa `knowledge-core.md:67` `all writes in single transaction across ALL layers` → `Metadata is truth, Vector/Graph/Raw derived via outbox, fail-open read` khớp engine doc + code `OutboxRow:41` + `unified.save:27`. Xóa `Rollback on failure` ở `knowledge-core.md:62`.
- **Verify:** `grep -rn "single transaction across ALL" docs/` = 0.

**Gate Phase 0:** `pytest -q` vẫn 36 pass, 4 file docs diff được review.

---

## Phase 1 — P0 Correctness/Security (Day 1-3)

### 1.1 Vector Chroma dead — P0 critical
- **File:** `src/pkh/storage/vector.py:126-137`, `src/pkh/storage/vector.py:14,99`, `config/settings.yaml.example:24`
- **Bug:** `ChromaVectorStore.query:133` tính `res` rồi bỏ, `return fallback.query:137` → sau restart mất vector.
- **Fix:**
  - Dùng `res` từ `self._collection.query`: `ids, distances, metadatas = res["ids"][0], res["distances"][0], res["metadatas"][0]` → map `distance→score=1/(1+dist)`, tôn trọng `filters:133` nếu có.
  - Dual-write đối xứng: `upsert:99` ghi Chroma + fallback (trong cùng try, fallback chỉ khi Chroma exception thì rollback).
  - `__init__:90` thêm `reconcile()` load Chroma → fallback khi start (warm cache).
  - `_simple_embedding:14` tôn trọng `settings.vector.embedding_model` nếu là `hash` thì giữ, nếu là `text-embedding-3-small` ghi TODO rõ.
- **Test:** `tests/unit/test_vector_restart.py` insert 3 KO → new `KnowledgeStore` → `search("query")` ≠ [].
- **Verify:** `ruff --select F841` không còn `res` unused, `pytest -k vector` pass.

### 1.2 Metadata query sai pagination + O(N) scan — P0
- **File:** `src/pkh/storage/metadata.py:138-189,192,222,246`, `src/pkh/storage/metadata.py:105`
- **Bug:** `query:164` fetch all rồi python `q in title:179` + slice `offset:189` → sai `limit/offset`, slow. `get_by_source:192` full scan. `count:222` deprecated.
- **Fix:**
  - `query`: `stmt = select(KnowledgeRow).where(KnowledgeRow.lifecycle_state.in_(...))` + `where(or_(title.ilike(f"%{q}%"), content.ilike(...), description.ilike(...)))` trước `limit/offset:168`. `source_type` filter thành `where` SQL, bỏ post-filter `171-173`.
  - Thêm index `title, content, lifecycle_state` trong `Base.metadata`.
  - `count` → `select(func.count()).select_from(KnowledgeRow)`.
  - `_row_to_ko:78` parse fail → `last_synced=None` thay `now()`.
- **Test:** `tests/unit/test_metadata_pagination.py` với 10 KO, `query(q, limit=3, offset=3)` trả đúng 3, `total` đúng.
- **Verify:** `pytest -k metadata` pass, `EXPLAIN QUERY PLAN` không còn full scan.

### 1.3 Async blocking — P0
- **Files:** `src/pkh/engines/ingestion/git_connector.py:18,68,96`, `src/pkh/storage/graph.py:31`, `src/pkh/storage/metadata.py:105`, `src/pkh/utils/logging.py:60`
- **Bug:** `subprocess.run` blocking trong `async def`, `write_text` sync, `create_engine sqlite://` sync.
- **Fix:**
  - `git_connector._run` → `await asyncio.to_thread(subprocess.run, ..., timeout=30)`.
  - `graph._persist:31` → `await asyncio.to_thread(Path.write_text, ...)`.
  - `metadata.py:105` → `create_async_engine("sqlite+aiosqlite:///...")` + `async_sessionmaker`, `insert_many:108` dùng `async with session.begin()`.
  - Hoặc nếu giữ sync engine thì wrap mọi DB call trong `to_thread`.
- **Test:** `pytest --timeout=2` không block loop, `asyncio` test với `pytest-asyncio`.
- **Verify:** `grep -rn "subprocess.run" src/pkh/engines/ingestion/` chỉ trong `to_thread`.

### 1.4 Lifecycle bypass — P0
- **Files:** `src/pkh/models/lifecycle.py:11-22,31`, `src/pkh/storage/metadata.py:251-255`, `src/pkh/api/main.py:95`, `src/pkh/cli/main.py:127`
- **Bug:** `VALID_TRANSITIONS:11` thừa `SUPERSEDED→ARCHIVED:21`, cycle `DEPRECATED→SUPERSEDED:22`, `metadata.update_lifecycle:255` ghi DB trực tiếp.
- **Fix:**
  - Xóa `DEPRECATED→SUPERSEDED:22` (hoặc ghi rationale cycle nếu giữ thì thêm guard `max 1 re-activation`). Xóa `SUPERSEDED→ARCHIVED` thừa.
  - `metadata.update_lifecycle` gọi `transition(KnowledgeObject(lifecycle_state=old), new_state):31` trước khi `row.lifecycle_state = new_state.value`.
  - API/CLI bỏ hack `if DISCOVERED→ACTIVE:95`, dùng `transition`.
  - `LifecycleStateMachine:48` xóa duplicate wrapper hoặc implement `can_transition`.
- **Test:** `tests/unit/test_lifecycle_transitions.py` cover 14 valid + 5 invalid.
- **Verify:** `grep -rn "row.lifecycle_state =" src/` chỉ trong `transition` guard.

### 1.5 Audit race — P0
- **File:** `src/pkh/governance/audit.py:17,21,50-52`, `src/pkh/config/settings.py:108` (GovernanceConfig)
- **Bug:** `log:52` append không lock → concurrent corrupt hash chain `SHA256(prev+payload):50`.
- **Fix:**
  - Thêm `filelock.FileLock(str(path)+".lock")` quanh `log:52` và `verify_chain:64`.
  - Path lấy từ `GovernanceConfig.audit_path` thay hard-code `./data/audit.jsonl:17`, `_last_hash:21` cache với `mtime` check.
  - `verify_chain` không mutate entry sau `json.loads` (copy trước khi pop `hash`).
- **Test:** `tests/unit/test_audit_concurrent.py` `asyncio.gather(10*log)` → `verify_chain` true.
- **Verify:** `pip show filelock` có, `pytest -k audit` pass.

### 1.6 Per-request store leak — P0
- **Files:** `src/pkh/api/main.py:33,58`, `src/pkh/cli/main.py:37`, `src/pkh/storage/unified.py:56,84`
- **Bug:** `get_store:33` tạo `KnowledgeStore` + `PersistentClient` mỗi request → leak `sqlite` (`ResourceWarning` đã thấy trong coverage).
- **Fix:**
  - FastAPI `lifespan` tạo 1 `KnowledgeStore` singleton, `get_store` yield singleton.
  - CLI `get_store:37` cache per process.
  - `health_check:84` `await metadata.count()` nếu async, `vector.count()` await đúng.
- **Test:** `tests/integration/test_api.py:17` chạy 10 requests liên tiếp không tăng `ResourceWarning`.
- **Verify:** `pytest -W error::ResourceWarning` 0 warning.

### 1.7 RBAC + path traversal — P0 security
- **Files:** `src/pkh/api/auth.py:9,18,28-36`, `src/pkh/api/main.py:65-66,114,179,225`, `pyproject.toml:22-23` (python-jose)
- **Bug:** `X-Role` spoof, `ingest/query` không check RBAC, `source: str|None:42` không validate `git://../../etc`.
- **Fix:**
  - `auth.get_current_role` đổi sang `Authorization: Bearer <JWT>` với `python-jose`, fallback `X-Role` chỉ khi `rbac_enabled=False` (đã có `ROLES:9`).
  - Thêm `Depends(get_current_role)` cho `POST /ingest`, `POST /query`, `POST /context`, `GET /audit:225`.
  - Validate `IngestRequest.source:42` bằng `Url` + whitelist `git://` + `Path.resolve().is_relative_to(repo_root)`, chặn `..`.
  - `pyproject.toml:22` `python-jose` đã có, thêm `PyJWT` nếu cần.
- **Test:** `tests/unit/test_rbac.py` 403 khi `X-Role: VIEWER` gọi `/ingest`, `test_path_traversal.py` `git://../../etc` 400.
- **Verify:** `pytest -k rbac` pass, `ruff` không còn `auth.py 25%` miss.

**Gate Phase 1:** `PYTHONPATH=src pytest -q` ≥42 tests (36+6 new), `ResourceWarning` 0, `vector restart` pass, `audit concurrent` pass, `ruff --select F841,B905` giảm 50%.

---

## Phase 2 — P1 Completeness (Day 4-6)

### 2.1 Outbox reconcile — P1
- **Files:** `src/pkh/storage/metadata.py:222-239,41`, `src/pkh/storage/unified.py:45-51,31-41`, `docs/engines/knowledge-storage-engine.md:218`
- **Bug:** `unified.save:45` loop `claim_outbox(100)` per KO re-claim cùng PENDING, không BG worker, không nightly check.
- **Fix:**
  - `claim_outbox:222` thêm `ORDER BY created_at FOR UPDATE SKIP LOCKED` (sqlite emulate bằng `WHERE status='PENDING' ORDER BY created_at LIMIT batch`).
  - `unified.save` fix ack loop: `rows=claim_outbox(batch=len(knowledge))` 1 lần, mark theo `id` không loop per KO.
  - Thêm `reconcile_pending()` chạy mỗi `save` hoặc cron, + `nightly_check` `count(metadata) vs vector/graph` như `storage-engine:218`.
- **Test:** `tests/unit/test_outbox.py` save 5 KO → kill vector → `reconcile` → vector đủ 5.
- **Verify:** `grep -rn "claim_outbox" src/` chỉ 1 call per save.

### 2.2 Ingestion pagination+auth — P1
- **Files:** `src/pkh/engines/ingestion/confluence_connector.py:40,70`, `jira_connector.py:31,69`, `document_connector.py:20,80`, `src/pkh/engines/ingestion/connectors.py:12`, `config/settings.yaml.example:24`
- **Bug:** `limit 50` không cursor, `Bearer` sai Atlassian, `get_item:70` NotImplemented, `patterns:20` lệch `*.json`.
- **Fix:**
  - Confluence/Jira: cursor pagination (`start` + `nextPageToken`), reuse 1 `AsyncClient` per connector (close trong `__aexit__`), auth `Basic` (`email:api_token` base64) cho Confluence, JQL escape `project="{proj}"`.
  - Implement `get_item:70` fetch single page/issue.
  - `document_connector patterns:20` sync với `settings.yaml.example` (`*.md,*.pdf,*.yaml,*.json`).
  - `connectors.py:12` Protocol thêm `@runtime_checkable`.
- **Test:** Mock `httpx` 100 items với `limit 50` → 2 pages, `test_get_item` pass.
- **Verify:** `pytest -k ingestion` cover >70% (hiện 23-32%).

### 2.3 Parser decorated + API drift — P1
- **File:** `src/pkh/engines/code_intelligence/parser.py:15,60-65,82,135,152,164,213,275,313,326`
- **Bug:** `Language(language()):20` deprecated, miss `async_function_definition`, `decorated_definition:152` pass, heuristic method sai, import regex只取首模块.
- **Fix:**
  - Upgrade `tree_sitter` API: `Language(tree_sitter_python.language())` → `tree_sitter.Language` mới hoặc `tree_sitter_python.language()` trực tiếp.
  - Thêm `async_function_definition` trong `_parse_with_treesitter:82`, unwrap `decorated_definition:152` lấy inner `function_definition`/`class_definition`.
  - Fix `FUNCTION vs METHOD:135` check `parent.type=="class_definition"`.
  - Import regex `164` split `import a, b` → từng module.
  - `superclasses:213` giữ `module.Class` thay `b.attr`.
  - `CodeParser.parse:326-329` không gọi private `_parse_with_regex`, tách helper public.
- **Test:** `tests/unit/test_code_parser_decorated.py` với `@decorator def f` + `async def` + `import a,b`.
- **Verify:** `coverage parser.py` 55% → 80%+.

### 2.4 Extraction dedup+cache — P1
- **Files:** `src/pkh/engines/extraction/extractor.py:20,73,91,139,156,203`, `src/pkh/engines/extraction/pipeline.py:48-52,64,98,130,136`
- **Bug:** Cache `hash(content):52` only → collision cross-source, `UUID` random → dedup không thể, `>21 KOs/doc`.
- **Fix:**
  - Cache key `(source_type.value, source_id, hash(content)):52` thay `hash(content)`, TTL dùng `cache_ttl_days:98` (lru + expire).
  - `extractor` cap: headings `139` limit 5, rules `156` 3, traces 5 → max ~10 KOs/doc.
  - UUID deterministic `uuid5(NAMESPACE, f"{source_id}:{kind}:{name}")` để re-ingest cùng id.
  - `budget_tokens:130` dùng `tiktoken` `len(encoding.encode(content))//1`, `stats.llm_calls` increment.
  - Business rule regex `156` thêm `r"\b(must|shall|cannot|required)\b"` word boundary.
- **Test:** `tests/unit/test_extraction_cache.py` same content 2 sources → 2 KO khác `source_references`.
- **Verify:** `pytest -k extraction` 1 test → 3 tests, `pipeline.py` 64% → 85%.

### 2.5 Retrieval concurrent + bỏ debug — P1
- **File:** `src/pkh/engines/retrieval/retriever.py:25,66-90,102-103,116-134,138-172`, `src/pkh/engines/retrieval/reranker.py:38,58`
- **Bug:** Sequential `await wait_for` trong loop, debug boost `knowledgeobject:102`, `tokens[:4]` cắt bừa, N+1 query.
- **Fix:**
  - Xóa `exact_boost+=3.0:102-103`.
  - `retrieve:138-158` → `results = await asyncio.gather(*[asyncio.wait_for(c, timeout=2) for c in coros], return_exceptions=True)` thay loop.
  - `tokens[:4]:83` → `tokens[:8]`, type_boost `1.0:105` → `0.2`.
  - `graph_search:116` batch `metadata.get` bằng `metadata.query(ids=neighbors)` thay N lần.
  - `reranker.deduplicate:58` dùng `knowledge.id` (nay deterministic) nên dedup có tác dụng.
- **Test:** `tests/unit/test_retrieval_concurrent.py` 3 stratégies chạy <0.4s song song.
- **Verify:** `pytest -k retrieval` pass, `retriever.py` 67% → 80%.

### 2.6 Context compressor — P1
- **Files:** `src/pkh/engines/context_delivery/compressor.py:13-76,44,54`, `src/pkh/engines/context_delivery/validator.py:20,25`, `src/pkh/engines/context_delivery/assembler.py:42,55,65`
- **Bug:** Tier2 empty không revert `if not knowledge: pass:44`, Tier4 skip không log, token `len//4` lệch.
- **Fix:**
  - Tier2 `if not knowledge: knowledge=snapshot:44` restore.
  - Tier4 comment `SKIP (llm_enabled=false)` → `warnings.append("Tier4 LLM summarize skipped (mock)"):59`.
  - Token thống nhất `max(1,len(c.content)//4)` cả `compressor:54` và `validator:20`.
  - `assembler:42` truncate theo token `tiktoken` 4000 thay char, `uniq_sources:55` dedup bằng `url` nếu có.
  - `compressor` không mutate input: `package.model_copy(deep=True)` trước khi cắt.
- **Test:** `tests/unit/test_compressor_empty.py` Tier2 empty → revert, `test_token_consistency` compressor vs validator cùng số.
- **Verify:** `compressor.py` 60% → 85%.

### 2.7 Adapter thực — P1
- **Files:** `src/pkh/adapters/base.py:10`, `src/pkh/adapters/mock.py:33`, `src/pkh/adapters/claude.py:9`, `gpt.py:11`, `gemini.py:6`, `local.py:6`, `src/pkh/config/settings.py:51`
- **Bug:** Tất cả kế thừa mock, `embedding_model` không dùng, `adapt` vs `format_context` drift.
- **Fix:**
  - Giữ Mock khi `llm_enabled=false` (theo `adr-004:15`), khi `true` gọi SDK thật (`anthropic`, `openai`) với `format_context` chuẩn. `GPTAdapter.format_context:10` đổi thành `{"model":..., "messages":[...]}`, `ClaudeAdapter:10` giữ prompt hiện tại nhưng xóa hard-code `101` char.
  - `embedding_model` nối vào `vector._simple_embedding` hoặc ghi `TODO: replace hash with text-embedding-3-small when OPENAI_API_KEY set`.
  - Thống nhất `base.py:10` `adapt` vs `format_context` theo `core/7:90` (giữ cả 2, `adapt` alias `format_context`).
  - `mock.py:33` xóa `ctx` unused.
- **Test:** `tests/unit/test_adapters_mock.py` `MockAdapter.format_context` trả đúng `knowledge_count`.
- **Verify:** `adapters/*` 75-100%, `ruff F841` 0.

**Gate Phase 2:** `pkh ingest --source git://./ && pkh query "How does PaymentService work?" && pkh context --as claude` trả `ContextPackage` có `sources` non-empty, `confidence` 0-1, lifecycle `ACTIVE`.

---

## Phase 3 — P2 Quality (Day 7-8)

### 3.1 Ruff/mypy — P2
- **Files:** `pyproject.toml:55-56,68`, `src/pkh/adapters/mock.py:33`, `parser.py:64-65`, `retriever.py:172`, `cli/main.py:209`
- **Fix:** `F841` remove `ctx/entities/relationships`, `B905` thêm `strict=True` `zip:172`, `E501` tách line 100 (`line-length 100`), `E741` đổi `l` → `label`. `mypy src/` pass với `ignore_missing_imports:71`.
- **Config:** Nâng `coverage fail_under 55:75` → `68` (thực tế) rồi `75` sau Phase 3, bỏ `omit src/pkh/cli/*:76`.
- **Verify:** `ruff check src/ tests/` 0 lỗi, `mypy src/` 0 lỗi.

### 3.2 Settings typed — P2
- **File:** `src/pkh/config/settings.py:14,51,83,108,146,123`
- **Fix:** `repos: list[GitRepoConfig]` (url, branch, auth), `provider: Literal["chroma","pgvector","memory"]`, `weights_per_intent: dict[IntentType, float]` default, `_settings` thread-safe `lru_cache`, tôn trọng `PKH_CONFIG_FILE` env, fallback `cls()` khi YAML thiếu → raise `PKHConfigError:123`.
- **Verify:** `pytest -k config` 3 → 5 tests, `mypy` không `Any` leak.

### 3.3 Logging — P2
- **File:** `src/pkh/utils/logging.py:60,28,70`
- **Fix:** Không `root.handlers.clear()` khi `uvicorn` running (`if not root.handlers` hoặc check `logging.getLogger("uvicorn")`), thêm `exc_info, stack_info` trong `format:28`.
- **Verify:** `uvicorn src.pkh.api.main:app --reload` log không mất.

### 3.4 Docs polish — P3
- **Files:** `docs/decisions/*`, `docs/glossary.md:8,40,208`, `docs/tech-stack.md:209,213`, `README.md:72,92`, `docs/plan/daily/README.md:27`
- **Fix:** Thêm ADR RBAC/JWT (6), sửa `glossary:8` thêm `entity_type`, sửa `tech-stack:213` `0.10x` → `0.101`, `README:72` `7 states` → `8`, sync `daily/README:27` mapping, `glossary:208` `Weaviate` ghi `alternative, not decision`.
- **Verify:** `grep -rn "7 states" README.md` =0.

### 3.5 Tests gap — P2
- **Files:** `tests/unit/*`, `tests/integration/*`, `pyproject.toml:73`
- **Thêm:**
  - `test_lifecycle_invalid.py` invalid transitions
  - `test_metadata_pagination.py` offset/limit
  - `test_vector_restart.py` persistence
  - `test_audit_concurrent.py` 10 concurrent log
  - `test_rbac_403.py` VIEWER 403
  - `test_path_traversal.py` `../../etc` 400
  - `test_parser_decorated.py` decorated async
  - `test_compressor_empty.py` revert
  - `test_outbox.py` reconcile
- **Target:** `pytest --cov --cov-report=term-missing` `total 67.79% → 75%+`, mỗi engine `>70%` (hiện `parser 55%, ingestion 23-57%`).

**Gate Phase 3:** `ruff 0`, `mypy 0`, `pytest --cov --cov-fail-under=75` pass, `git tag v0.1.0-mvp` + `CHANGELOG.md` + `known limitations` (ghi thẳng gì chưa làm: multi-lang, Neo4j/S3).

---

## Phụ lục — Checklist nhanh

### P0 (8 tasks) — Must
- [ ] 1.1 vector.py:133 dùng res
- [ ] 1.2 metadata.py:138 ilike + limit pushdown
- [ ] 1.3 async to_thread
- [ ] 1.4 lifecycle transition guard
- [ ] 1.5 audit filelock
- [ ] 1.6 store singleton + ResourceWarning 0
- [ ] 1.7 RBAC + path traversal
- [ ] 0.1-0.4 docs truth

### P1 (7 tasks) — Should
- [ ] 2.1 outbox reconcile
- [ ] 2.2 ingestion pagination+auth
- [ ] 2.3 parser decorated
- [ ] 2.4 extraction cache+UUID
- [ ] 2.5 retrieval concurrent
- [ ] 2.6 compressor revert
- [ ] 2.7 adapter SDK

### P2 (5 tasks) — Polish
- [ ] 3.1 ruff/mypy 0
- [ ] 3.2 settings typed
- [ ] 3.3 logging uvicorn safe
- [ ] 3.4 docs polish
- [ ] 3.5 tests 75%+

### Lệnh verify tổng (chạy sau mỗi phase)
```bash
PYTHONPATH=src pytest tests/ -q
PYTHONPATH=src pytest tests/ --cov=src/pkh --cov-report=term-missing --cov-fail-under=75
ruff check src/ tests/
mypy src/
PYTHONPATH=src python -m pkh --help
```

### Rủi ro & Mitigation
| Rủi ro | Mitigation |
|--------|------------|
| Đổi `metadata` sang `aiosqlite` vỡ `Storage` API | Giữ sync fallback 1 phase, `to_thread` trước, async sau |
| Chroma API đổi 0.4→0.5 | Pin `chromadb>=0.4,<0.6` trong `pyproject.toml:27`, test restart cover |
| Taxonomy đổi vỡ existing DB `./data/pkh.db` | Migration script `ALTER` hoặc `rm data/pkh.db` trong dev, ghi `BREAKING` trong CHANGELOG |

---

## Liên kết
- Master plan: `docs/plan/plan.md`
- Daily: `docs/plan/daily/README.md`
- ADRs: `docs/decisions/adr-002-storage.md`, `adr-003-code-parsing.md`, `adr-004-llm-adapter.md`, `adr-005-retrieval.md`
- Core: `docs/core/3-knowledge-model.md`, `4-knowledge-lifecycle.md`, `5-source-of-truth-model.md`
