"""Reranker + Deduplicator."""

from __future__ import annotations

from datetime import datetime, timezone

from pkh.models.knowledge import KnowledgeObject, LifecycleState


def lifecycle_bonus(state: LifecycleState) -> float:
    if state == LifecycleState.ACTIVE:
        return 1.0
    if state == LifecycleState.UPDATED:
        return 0.5
    if state in (LifecycleState.VALIDATING, LifecycleState.EXTRACTED):
        return 0.3
    return 0.0


def recency_score(updated_at: datetime) -> float:
    try:
        now = datetime.now(timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        delta_days = (now - updated_at).days
        # 0 days =1.0, 30 days=0.5, 90 days=0.2
        if delta_days <= 7:
            return 1.0
        if delta_days <= 30:
            return 0.7
        if delta_days <= 90:
            return 0.4
        return 0.1
    except Exception:
        return 0.5


def rerank(
    items: list[tuple[KnowledgeObject, float]],
    confidence_weight: float = 0.3,
    lifecycle_weight: float = 0.2,
    recency_weight: float = 0.1,
    relevance_weight: float = 0.4,
) -> list[tuple[KnowledgeObject, float]]:
    reranked = []
    for ko, relevance in items:
        score = (
            confidence_weight * ko.confidence
            + lifecycle_weight * lifecycle_bonus(ko.lifecycle_state)
            + recency_weight * recency_score(ko.updated_at)
            + relevance_weight * min(max(relevance, 0.0), 1.0)
        )
        reranked.append((ko, score))
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


def deduplicate(items: list[tuple[KnowledgeObject, float]]) -> list[tuple[KnowledgeObject, float]]:
    seen: dict[str, tuple[KnowledgeObject, float]] = {}
    for ko, score in items:
        if ko.id not in seen or score > seen[ko.id][1]:
            seen[ko.id] = (ko, score)
    result = list(seen.values())
    result.sort(key=lambda x: x[1], reverse=True)
    return result
