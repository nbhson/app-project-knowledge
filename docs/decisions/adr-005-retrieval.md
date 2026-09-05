# ADR-005: Hybrid Retrieval — RRF (k=60) + 5-Tier Compression

Date: 2026-09-06
Status: Accepted
Related: docs/core/6-retrieval-strategy.md, docs/engines/retrieval-intelligence-engine.md, docs/engines/context-delivery-engine.md

## Context

Cần tìm knowledge cho 8 intent types (CODE_UNDERSTANDING, IMPACT_ANALYSIS...). Mỗi intent hợp với strategy khác (vector cho semantic, keyword cho exact, graph cho traversal). Làm sao fuse kết quả mà không cần calibrate score?

## Decision

- **Hybrid execution:** Chạy **Vector + Keyword + Graph** song song, mỗi strategy timeout 200ms, trả về partial nếu timeout.
- **Fusion:** **Reciprocal Rank Fusion (RRF)** với `k=60`: `score = Σ 1/(k + rank_in_strategy)`. Không cần score chuẩn hóa, robust với các strategy khác scale.
- **Weights per intent:** Config `retrieval.weights[INTENT][strategy]` để ARCHITECTURE thiên vector, IMPACT_ANALYSIS thiên graph, v.v.
- **Post-fusion:** Reranking (confidence 0.3 + lifecycle 0.2 + recency 0.1 + relevance 0.3), deduplication giữ highest confidence.
- **Compression:** 5-tier (confidence prune → lifecycle prune → relevance top-K → LLM summarize → relationship prune) để fit context window, log vào `compression_log`.

## Consequences

- (+) RRF đơn giản, proven, không cần training.
- (+) Thêm strategy mới không phải recalibrate — chỉ cần thêm vào RRF.
- (-) RRF không tận dụng absolute score — nếu một strategy rất confident, không boost hơn rank 1.
- (-) 5-tier compression cần token counting chính xác (tiktoken) và có thể mất info nếu prune quá mạnh.

## Alternatives Considered

- **Weighted sum of scores:** cần normalize score từ 3 hệ khác nhau — khó và brittle.
- **Learning-to-rank (LTR):** cần training data lớn, không có ở MVP.
- **Chỉ vector-only:** đủ cho MVP nhưng miss IMPACT_ANALYSIS và REQUIREMENT_TRACEABILITY cần graph.

## MVP Simplification

- MVP chỉ chạy **vector-only** (không RRF, không graph). RRF + graph traversal thêm ở Phase 5 Day 21-22 sau khi vector ổn.
