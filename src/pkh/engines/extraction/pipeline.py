"""3-pass extraction pipeline: rule -> LLM enrichment -> confidence scoring."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from pkh.adapters.base import ModelAdapter
from pkh.engines.code_intelligence.parser import CodeParser
from pkh.engines.extraction.extractor import (
    extract_from_code,
    extract_from_document,
    extract_from_jira,
)
from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import KnowledgeObject, SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class ExtractionStats:
    def __init__(self):
        self.inputs_processed = 0
        self.entities_extracted = 0
        self.relationships_extracted = 0
        self.decisions_extracted = 0
        self.rules_extracted = 0
        self.avg_confidence = 0.0
        self.llm_calls = 0
        self.duration_seconds = 0.0


class ExtractionPipeline:
    def __init__(
        self,
        llm_enabled: bool = False,
        llm_adapter: ModelAdapter | None = None,
        budget_tokens: int = 50000,
        batch_size: int = 15,
    ):
        self.llm_enabled = llm_enabled
        self.llm_adapter = llm_adapter
        self.budget_tokens = budget_tokens
        self.batch_size = batch_size
        self.code_parser = CodeParser()
        self._cache: dict[str, list[KnowledgeObject]] = {}
        self._tokens_used = 0

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    async def run(self, items: list[RawItem]) -> tuple[list[KnowledgeObject], dict[str, Any]]:
        start = time.time()
        all_kos: list[KnowledgeObject] = []
        stats = ExtractionStats()
        stats.inputs_processed = len(items)

        for item in items:
            if not item.content or not item.content.strip():
                logger.warning(f"Skipping empty content item {item.item_id}")
                continue
            h = self._hash(item.content)
            if h in self._cache:
                all_kos.extend(self._cache[h])
                continue

            try:
                # Pass 1: rule-based
                kos = await self._rule_extract(item)
                # Pass 2: LLM enrichment if enabled
                if self.llm_enabled and self.llm_adapter and self._tokens_used < self.budget_tokens:
                    kos = await self._llm_enrich(kos, item)
            except Exception as e:
                logger.warning(f"Extraction failed for {item.item_id}: {e}")
                continue

            self._cache[h] = kos
            all_kos.extend(kos)

        # Pass 3: confidence calibration (simple: boost rule-based, demote low)
        # Already assigned in extractors.

        stats.entities_extracted = sum(1 for k in all_kos if k.object_type.value == "ENTITY")
        stats.relationships_extracted = sum(
            1 for k in all_kos if k.object_type.value == "RELATIONSHIP"
        )
        stats.decisions_extracted = sum(1 for k in all_kos if k.object_type.value == "DECISION")
        stats.rules_extracted = sum(1 for k in all_kos if k.object_type.value == "RULE")
        if all_kos:
            stats.avg_confidence = sum(k.confidence for k in all_kos) / len(all_kos)
        stats.duration_seconds = time.time() - start
        # also auto validation: ensure source refs non-empty, confidence in [0,1], etc already validated by pydantic

        return all_kos, {
            "inputs_processed": stats.inputs_processed,
            "entities_extracted": stats.entities_extracted,
            "relationships_extracted": stats.relationships_extracted,
            "decisions_extracted": stats.decisions_extracted,
            "rules_extracted": stats.rules_extracted,
            "avg_confidence": stats.avg_confidence,
            "llm_calls": stats.llm_calls,
            "duration_seconds": stats.duration_seconds,
        }

    async def _rule_extract(self, item: RawItem) -> list[KnowledgeObject]:
        # dispatch by source_type or content_type
        if item.source_type == SourceType.GIT.value and item.content_type in ("python", "text"):
            # if python file, parse code
            if item.item_id.endswith(".py"):
                code_out = self.code_parser.parse(item.item_id, item.content)
                return extract_from_code(code_out, item)
            else:
                # non-py code file still as document but with file entity
                return extract_from_document(item)
        elif item.source_type == SourceType.JIRA.value:
            return extract_from_jira(item)
        elif item.source_type == SourceType.CONFLUENCE.value:
            return extract_from_document(item)
        else:
            return extract_from_document(item)

    async def _llm_enrich(self, kos: list[KnowledgeObject], item: RawItem) -> list[KnowledgeObject]:
        # Simple placeholder: call adapter to enrich if available
        if not self.llm_adapter:
            return kos
        try:
            # estimate tokens
            est_tokens = len(item.content) // 4 + 500
            if self._tokens_used + est_tokens > self.budget_tokens:
                logger.warning("LLM budget exceeded, skipping")
                return kos
            self._tokens_used += est_tokens
            # mock enrichment: if adapter has method enrich, call it; else do nothing
            if hasattr(self.llm_adapter, "enrich"):
                extra = await self.llm_adapter.enrich(item.content)  # type: ignore
                # extra expected to be list[KnowledgeObject] dicts
                for e in extra or []:
                    # already KnowledgeObject
                    kos.append(e)
        except Exception as e:
            logger.warning(f"LLM enrich failed: {e}")
        return kos
