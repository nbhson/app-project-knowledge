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


def _dedupe_key(ko: KnowledgeObject) -> str:
    """Deterministic fingerprint for dedup.

    Uses id when deterministic (uuid5), but falls back to content
    fingerprint to catch duplicates even when ids are random uuid4.
    """
    # primary: id, secondary: title+content+entity_type (lower, stripped)
    # Ensures dedup triggers regardless of UUID randomness.
    t = ko.title.strip().lower()
    c = ko.content.strip().lower()
    content_fp = f"{t}|{c}|{ko.entity_type}|{ko.object_type}"
    return f"{ko.id}::{hash(content_fp)}"


def _content_fingerprint(ko: KnowledgeObject) -> str:
    t = ko.title.strip().lower()
    c = ko.content.strip().lower()[:500]
    return f"{t}::{c}::{ko.entity_type}::{ko.object_type}"


def deduplicate(items: list[tuple[KnowledgeObject, float]]) -> list[tuple[KnowledgeObject, float]]:
    seen_by_id: dict[str, tuple[KnowledgeObject, float]] = {}
    seen_by_content: dict[str, str] = {}  # fingerprint -> id that won
    for ko, score in items:
        fp = _content_fingerprint(ko)
        # if we have seen same content before, keep higher score
        if fp in seen_by_content:
            existing_id = seen_by_content[fp]
            # keep higher score among duplicates
            if score > seen_by_id[existing_id][1]:
                # replace: remove old id entry, add new
                del seen_by_id[existing_id]
                seen_by_id[ko.id] = (ko, score)
                seen_by_content[fp] = ko.id
            # else skip duplicate
            continue
        # id-based dedup (deterministic ids)
        if ko.id not in seen_by_id or score > seen_by_id[ko.id][1]:
            # if this id was previously stored under different fp? not possible
            # but handle update
            if ko.id in seen_by_id:
                # remove old fp mapping
                old_ko = seen_by_id[ko.id][0]
                old_fp = _content_fingerprint(old_ko)
                seen_by_content.pop(old_fp, None)
            seen_by_id[ko.id] = (ko, score)
            seen_by_content[fp] = ko.id
    result = list(seen_by_id.values())
    result.sort(key=lambda x: x[1], reverse=True)
    return result
