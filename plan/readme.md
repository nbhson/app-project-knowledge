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

## Trạng thái

- [x] Plan
- [x] Fix #1–#13
- [x] `ast.parse` 10 files OK; pytest **87/87 pass** (unit 84 + integration 3)
- [x] Commit + self-review

## Review Log

### Vòng 1
- Self-review bắt 2 lỗi tự gây: (1) `unified.py` edit làm mất signature `__init__` (chỉ còn body — IndentationError); (2) `main.py` edit làm mất dòng `adapter = get_adapter(...)` (test không bắt vì handler không được cover ở nhánh đó — grep và khôi phục thủ công); (3) `_html_to_text` bản đầu truyền nhầm module `html` vào `re.sub` — test `test_confluence_page_to_raw` bắt được (TypeError got 'module'). Cả 3 đã sửa.
- `claim_outbox` đổi behavior: test storage pass với expunge fix. Audit finding trước đây "commit trước select" trong bản nháp đã chỉnh lại thành expunge-before-commit (đúng kiểu SQLAlchemy).
- `main.py` lifespan giờ clear `_store`/`_store_key` — `get_store` recreate khi cần; coherence đã verify qua integration tests.
