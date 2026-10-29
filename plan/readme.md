# Plan — app-project-knowledge

> PKH (Project Knowledge Hub): FastAPI + SQLAlchemy (SQLite) + Chroma vector + networkx
> graph. Ingest từ Confluence/Jira/Git/Documents → extraction pipeline → retrieval/query.

## Kết quả Review (audit đợt 1)

| # | Severity | Vị trí | Vấn đề | Fix |
|---|----------|--------|--------|-----|
| 1 | MAJOR | engines/ingestion/confluence_connector.py:83 | `body.storage` HTML raw từ Confluence lưu nguyên văn, `/query` + `/context` echo lại verbatim → stored XSS với mọi consumer render kết quả | `_html_to_text`: strip tags + decode entities; `content_type="text"` |
| 2 | MAJOR | storage/metadata.py:224-297 | LIKE/ILIKE không escape `%`/`_` user-controlled → wildcard injection, filter bypass (query, source_type, get_by_source) | Escape `\`/`%`/`_` + `escape="\"` clause (clause này trước đây hoàn toàn thiếu — escaping inert) |
| 3 | MAJOR | storage/metadata.py:281-297 | `claim_outbox` chỉ SELECT PENDING không flip status — 2 worker chạy đồng thời claim TRÙNG rows | Atomic claim: UPDATE PENDING→CLAIMED kèm claim-token trong `payload.claim` + SELECT theo token, expunge trước commit |
| 4 | MAJOR | api/main.py:246+ | Blocking disk I/O (`audit.log`, `audit.list`+`verify_chain`, `graph.get_neighbors`) chạy trực tiếp trong `async def` — block event loop | `asyncio.to_thread` ở 4 handler |
| 5 | MAJOR | api/main.py:274-276 | `/query` trả `detail=str(e)` cho ConfigurationError/AdapterError — AdapterError nhúng upstream URL + status + ≤500 ký tự response body | Generic 400/502 message, chi tiết chỉ `logger` server-side |
| 6 | MINOR | api/auth.py:50 | 401 detail `f"Invalid token: {e}"` — JWT lib có thể echo token segments/claims | Generic "Invalid token" + logger.warning |
| 7 | MINOR | api/main.py:312,323 | `__import__("os").getenv(...)` inline import hack ×2 | `import os` đầu module |
| 8 | MINOR | api/main.py:58 | lifespan không close store — SQLite engine/Chroma client sống qua shutdown | `KnowledgeStore.close()` mới (dispose metadata engine) gọi trong shutdown |
| 9 | MINOR | storage/graph.py:33-39 | `write_text` trực tiếp lên `graph.json` — crash giữa chừng corrupt store | Atomic: tmp + `os.replace` |
| 10 | MINOR | engines/extraction/pipeline.py:58,118 | `_cache` mọc vô hạn trong một `/ingest` call (giữ cả corpus trong RAM) | Bound 500 entries, evict oldest |
| 11 | MINOR | engines/retrieval/reranker.py:58-69 | `_dedupe_key` dead code dùng builtin `hash()` (non-deterministic giữa các process) | Xóa; test import nó đã cập nhật |
| 12 | MINOR | engines/ingestion/document_connector.py:112 | Truncate 2000 files im lặng | `logger.warning` khi truncate |
| 13 | MINOR | engines/ingestion/git_connector.py:19 | `subprocess.run(["git"...])` PATH lookup (ruff S607) | Lazy-resolved `_git()` qua `shutil.which` — raise SourceError rõ ràng nếu thiếu |

## Không sửa (đã cân nhắc, ghi nhận)

- **governance/audit.py:102-131** — `list()`/`verify_chain()` đọc toàn bộ log file (≤10MB) mỗi request; tail-read dòng 45-47 có thể split dòng cuối → false chain failures. Cần restructure streaming/tail parser — follow-up lớn hơn lợi ích ngay.
- **storage/vector.py:283-293** — `query(filters=...)` bỏ qua mọi filter trừ `lifecycle_states` mà không báo. Ghi nhận; thêm `raise` có thể phá caller đang (sai) dựa vào behavior im lặng — follow-up cần review callers.
- **engines/ingestion/sync_manager.py:29-31** — cursor dùng `item_id` cuối làm cursor (connector Confluence/Jira hiểu nhầm là offset/token). Cần per-source page cursor design — follow-up.

## Round 2 (2026-10-29) — Deep review + enterprise upgrade

### Kết quả Review đợt 2

| # | Severity | Vị trí | Vấn đề | Fix |
|---|----------|--------|--------|-----|
| R2-1 | MAJOR (perf) | git_connector.py `list_items` | 2 subprocess `git log` **mỗi file** — repo 500 files → 1000 processes | 1 lần `git log --name-only --format="%H %ct"` duy nhất → map path→(hash,ts) |
| R2-2 | MAJOR (dup) | cli/main.py + api/main.py | Source-URL→connector + lifecycle→ACTIVE duplicated 2 nơi (~80 dòng) | `pkh/services/ingest.py`: `build_connector()`, `activate_to_active()` |
| R2-3 | MODERATE (dup) | cli/main.py + api/main.py | Store singleton `_store_key_from_settings`/`_create_store` copy y nhau | `pkh/services/store.py`: shared factory `get_shared_store()` |
| R2-4 | MODERATE (bug) | git_connector.py:102,105 | `_run(["git", ...])` bare "git" — bypass `_git()` (round 1 chỉ fix 1 chỗ) | Dùng `_git()` |
| R2-5 | MODERATE (robust) | audit.py `list`/`verify_chain` | 1 dòng JSON hỏng → crash toàn bộ list/verify | Skip dòng malformed + warning; verify_chain vẫn fail-closed nếu chain sai |
| R2-6 | MODERATE (ergonomics) | CLI | Không `--verbose/--quiet/--json/--config`, không progress feedback, exit code ingest luôn 0 dù fail, help tối giản | Global flags + Rich progress + exit codes chuẩn (0 ok / 1 runtime / 2 config) + `--config` |
| R2-7 | MINOR (robust) | adapters/__init__.py | `except Exception: pass` quanh get_settings → config lỗi im lặng fallback MockAdapter | Chỉ swallow ConfigurationError có log; ném lại lỗi khác |
| R2-8 | MINOR (dup) | graph.py | `upsert` vs `upsert_many` copy logic edge/node | Extract `_apply_ko()` |
| R2-9 | MINOR (typing) | sync_manager, cli `_resolve_cli_adapter`, retriever | Thiếu type hints | Bổ sung |
| R2-10 | MINOR | cli sync | Không setup_logging, không audit | Dùng chung ingest path |

### Feature mới (đợt 2)

1. **`pkh export`** — export KOs ra `json`/`csv`/`markdown`, filter theo lifecycle/entity_type, `--out FILE` (stdout nếu thiếu).
2. **Logging modes** — `--verbose`/`--quiet`/`--json` global + env `PKH_LOG_LEVEL`; CLI mặc định human-readable console (không còn JSON noise trên terminal), API giữ JSON.
3. **`pkh doctor`** — health check môi trường: config resolution, storage paths writable, git binary, audit chain, providers summary; exit 1 khi fail.
4. **Global `--config` flag** — trỏ settings YAML tùy ý (trước đây chỉ qua env `PKH_CONFIG_FILE`).

### Không sửa đợt 2 (ghi nhận tiếp)

- sync_manager cursor = item_id cuối (cần per-source page cursor design — như round 1).
- FAILED outbox claim trong `reconcile_pending` chưa atomic như PENDING (2 worker đồng thời có thể retry trùng — idempotent fan-out nên harmless; follow-up).
- vector.query(filters=...) bỏ filter im lặng — giữ nguyên như round 1.

## Trạng thái

- [x] Plan
- [x] Fix #1–#13 (Round 1)
- [x] `ast.parse` 10 files OK; pytest **87/87 pass** (unit 84 + integration 3)
- [x] Commit + self-review

## Round 2 Trạng thái

- [x] Plan
- [x] R2-1..R2-10 + features
- [x] pytest green (baseline 87/87 với PYTHONPATH=src)
- [x] Commits local-only + self-review

### Round 2 — hoàn tất phần feature (subagent đợt sau, 2026-10-29)

WIP dang dở của session trước (CLI features) đã được review, hoàn thiện và
commit. Verify bằng smoke test CLI thật + thêm 19 unit test (tổng 106/106 pass).

Bổ sung trong đợt hoàn tất:

| # | Vị trí | Vấn đề | Fix |
|---|--------|--------|-----|
| F1 | storage/vector.py | chroma 0.5.x bắn telemetry kể cả khi `anonymized_telemetry=False` (bug chroma + posthog mới) → mọi CLI command in ERROR line đáng sợ | Tắt telemetry trong client settings + silence logger `chromadb.telemetry.product.posthog` |
| R2-6b | cli export | Validate `--format` SAU khi mở store/query DB → fail-late | Validate format trước khi đụng store (fail fast, exit 2) |
| R2-9b | cli graph | `get_store()` không qua `_settings_or_exit()` → ConfigurationError traceback thay vì message sạch | Guard `_settings_or_exit()` |
| R2-9c | utils/logging.py | `ConsoleFormatter` dùng `datetime.now()` thay vì `record.created` → sai timestamp khi log bị buffer | Dùng `record.created` |

Test thêm: `tests/unit/test_round2_features.py` (19 tests — export render/escape,
doctor checks, CLI export/doctor, console formatter, verbose/quiet/env levels).
Test expose 2 bug thật: `get_settings()` singleton cache dính pollution giữa
các test (fix bằng `reset_settings()` fixture) và env var đúng là
`PKH_STORAGE__VECTOR__PATH` (nested `__`), không phải `PKH_STORAGE__VECTOR_PATH`.

## Round 2 Trạng thái (final)

- [x] Plan + R2-1..R2-10 + features (export, logging modes, doctor, --config)
- [x] pytest **106/106 pass** (87 baseline + 19 mới), ruff + mypy sạch
- [x] Smoke CLI: ingest/doctor/export (--format json|csv|markdown, stdout/--out,
      exit 2 cho format/filter sai), doctor --json, telemetry noise đã sạch
- [x] Commits local-only + self-review

## Review Log

### Vòng 1
- Self-review bắt 2 lỗi tự gây: (1) `unified.py` edit làm mất signature `__init__` (chỉ còn body — IndentationError); (2) `main.py` edit làm mất dòng `adapter = get_adapter(...)` (test không bắt vì handler không được cover ở nhánh đó — grep và khôi phục thủ công); (3) `_html_to_text` bản đầu truyền nhầm module `html` vào `re.sub` — test `test_confluence_page_to_raw` bắt được (TypeError got 'module'). Cả 3 đã sửa.
- `claim_outbox` đổi behavior: test storage pass với expunge fix. Audit finding trước đây "commit trước select" trong bản nháp đã chỉnh lại thành expunge-before-commit (đúng kiểu SQLAlchemy).
- `main.py` lifespan giờ clear `_store`/`_store_key` — `get_store` recreate khi cần; coherence đã verify qua integration tests.
