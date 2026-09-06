"""5-tier compression."""

from __future__ import annotations

from pkh.engines.context_delivery.models import ContextPackage


def _count_tokens(text: str) -> int:
    # unified token estimate: approx 4 chars per token, at least 1
    # must match validator token count
    return max(1, len(text) // 4)


def compress(package: ContextPackage, max_tokens: int = 8000) -> ContextPackage:
    # do not mutate input
    package = package.model_copy(deep=True)

    total = sum(_count_tokens(c.content) for c in package.knowledge)
    if total <= max_tokens:
        return package

    # Tier1: confidence <0.3 prune
    before = len(package.knowledge)
    package.knowledge = [c for c in package.knowledge if c.confidence >= 0.3]
    if before != len(package.knowledge):
        package.warnings.append(
            f"Tier1 confidence pruning removed {before - len(package.knowledge)} chunks"
        )
        if package.search_stats:
            package.search_stats.compression_log.append(
                {"tier": 1, "removed": before - len(package.knowledge)}
            )
        total = sum(_count_tokens(c.content) for c in package.knowledge)
        if total <= max_tokens:
            return package

    # Tier2: lifecycle pruning - keep ACTIVE/UPDATED only
    snapshot = list(package.knowledge)
    before = len(package.knowledge)
    package.knowledge = [
        c
        for c in package.knowledge
        if str(c.lifecycle_state)
        in ("ACTIVE", "UPDATED", "LifecycleState.ACTIVE", "LifecycleState.UPDATED")
        or c.lifecycle_state in ("ACTIVE", "UPDATED")
    ]
    # if too aggressive and removes everything, revert
    if not package.knowledge:
        package.knowledge = snapshot
    else:
        if before != len(package.knowledge):
            package.warnings.append(
                f"Tier2 lifecycle pruning removed {before - len(package.knowledge)} chunks"
            )
            if package.search_stats:
                package.search_stats.compression_log.append(
                    {"tier": 2, "removed": before - len(package.knowledge)}
                )
        total = sum(_count_tokens(c.content) for c in package.knowledge)
        if total <= max_tokens:
            return package

    # Tier3: relevance top-K
    package.knowledge.sort(key=lambda c: c.relevance_score, reverse=True)
    kept = []
    tokens = 0
    for c in package.knowledge:
        t = _count_tokens(c.content)
        if tokens + t > max_tokens:
            break
        kept.append(c)
        tokens += t
    removed = len(package.knowledge) - len(kept)
    if removed > 0:
        package.warnings.append(f"Tier3 relevance truncation removed {removed} chunks")
        if package.search_stats:
            package.search_stats.compression_log.append({"tier": 3, "removed": removed})
    package.knowledge = kept
    if package.knowledge:
        ratio = total / max(sum(_count_tokens(c.content) for c in kept), 1)
        package.compression_ratio = ratio

    # Tier4: LLM summarize skipped in MVP (llm_enabled=false)
    # log as warning so consumer knows tier was considered but skipped
    package.warnings.append("Tier4 LLM summarize skipped (mock)")
    if package.search_stats:
        package.search_stats.compression_log.append(
            {"tier": 4, "skipped": True, "reason": "llm_enabled=false"}
        )

    # Tier5: relationship pruning
    if len(package.relationships) > 20:
        package.relationships = [r for r in package.relationships if r.confidence >= 0.5][:20]
        package.warnings.append("Tier5 relationship pruning applied")
        if package.search_stats:
            package.search_stats.compression_log.append({"tier": 5, "pruned": True})

    return package
