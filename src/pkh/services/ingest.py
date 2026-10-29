"""Shared ingestion pipeline used by both CLI (`pkh ingest`) and API (`POST /ingest`).

Round 2 dedup: source-URL parsing, connector construction, extraction pipeline
wiring, and lifecycle activation to ACTIVE previously existed as two drifting
copies. This module is the single implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pkh.adapters import get_adapter
from pkh.config.settings import Settings
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.confluence_connector import ConfluenceConnector
from pkh.engines.ingestion.document_connector import DocumentConnector
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.jira_connector import JiraConnector
from pkh.engines.ingestion.models import RawItem
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.models.knowledge import KnowledgeObject, LifecycleState
from pkh.models.lifecycle import transition as lifecycle_transition
from pkh.storage.unified import KnowledgeStore
from pkh.utils.exceptions import SourceError
from pkh.utils.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_SCHEMES = ("git://", "confluence://", "jira://", "document://")


@dataclass
class IngestOutcome:
    """Per-source result so callers can report partial failures cleanly."""

    source: str
    items_collected: int = 0
    kos_extracted: int = 0
    transition_failures: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def build_connector(src: str, settings: Settings):
    """Map a source URL (`git://path`, `confluence://SPACE`, `jira://PROJ`,
    `document://path`, or bare local path) to a connector.

    Raises SourceError on empty/unknown source payloads so callers can surface
    a clear message instead of constructing a broken connector.
    """
    if src.startswith("git://"):
        path = src[len("git://") :]
        if not path:
            raise SourceError("git source requires a path (git://./path)")
        return GitConnector(repo_url=path)
    if src.startswith("confluence://"):
        space = src[len("confluence://") :]
        return ConfluenceConnector(
            base_url=settings.sources.confluence.url, spaces=[space] if space else []
        )
    if src.startswith("jira://"):
        proj = src[len("jira://") :]
        return JiraConnector(base_url=settings.sources.jira.url, projects=[proj] if proj else [])
    if src.startswith("document://"):
        p = src[len("document://") :]
        if not p:
            raise SourceError("document source requires a path (document://./docs)")
        return DocumentConnector(paths=[p])
    # bare value: treat as local git path
    return GitConnector(repo_url=src)


def build_extraction_pipeline(settings: Settings) -> ExtractionPipeline:
    return ExtractionPipeline(
        llm_enabled=settings.extraction.llm_enabled,
        llm_adapter=(
            get_adapter(settings.extraction.llm_adapter)
            if settings.extraction.llm_enabled
            else None
        ),
        budget_tokens=settings.extraction.budget_per_run_tokens,
        batch_size=settings.extraction.batch_size,
    )


# Allowed direct jumps to ACTIVE from each intermediate state (forward path only).
_ACTIVATION_PATH: dict[LifecycleState, list[LifecycleState]] = {
    LifecycleState.DISCOVERED: [
        LifecycleState.EXTRACTED,
        LifecycleState.VALIDATING,
        LifecycleState.ACTIVE,
    ],
    LifecycleState.EXTRACTED: [LifecycleState.VALIDATING, LifecycleState.ACTIVE],
    LifecycleState.VALIDATING: [LifecycleState.ACTIVE],
}


def activate_to_active(
    kos: list[KnowledgeObject], reason: str = "ingest"
) -> tuple[list[KnowledgeObject], int]:
    """Walk the lifecycle state machine to ACTIVE where valid.

    Returns (objects, failure_count). Invalid transitions keep the original
    state (never cheat the state machine) and are logged + counted.
    """
    transitioned: list[KnowledgeObject] = []
    failures = 0
    for ko in kos:
        cur = ko.lifecycle_state
        path = _ACTIVATION_PATH.get(cur)
        if not path:
            transitioned.append(ko)
            continue
        try:
            for state in path:
                ko = lifecycle_transition_safe(ko, state, reason)
        except Exception as e:  # LifecycleError from the state machine
            logger.warning(f"Lifecycle transition failed for {ko.id}: {e}")
            failures += 1
        transitioned.append(ko)
    return transitioned, failures


def lifecycle_transition_safe(
    ko: KnowledgeObject, target: LifecycleState, reason: str
) -> KnowledgeObject:
    """Single-hop transition wrapper (kept for future validation hooks)."""
    return lifecycle_transition(ko, target, reason)


async def ingest_source(
    store: KnowledgeStore,
    src: str,
    settings: Settings,
    *,
    reason: str = "ingest",
    on_progress: Callable[[str], None] | None = None,
) -> IngestOutcome:
    """Collect -> extract -> activate -> save for one source URL.

    `on_progress(detail)` is an optional callback for UI feedback.
    """
    try:
        conn = build_connector(src, settings)
        mgr = SyncManager([conn])
        items: list[RawItem] = await mgr.collect_all()
        if on_progress:
            on_progress(f"collected {len(items)} raw items")
        if not items:
            return IngestOutcome(source=src, items_collected=0)
        pipeline = build_extraction_pipeline(settings)
        kos, _stats = await pipeline.run(items)
        if on_progress:
            on_progress(f"extracted {len(kos)} knowledge objects")
        kos, failures = activate_to_active(kos, reason=reason)
        await store.save(kos)
        return IngestOutcome(
            source=src,
            items_collected=len(items),
            kos_extracted=len(kos),
            transition_failures=failures,
        )
    except Exception as e:
        logger.warning(f"Ingest failed for {src}: {e}")
        return IngestOutcome(source=src, error=str(e))
