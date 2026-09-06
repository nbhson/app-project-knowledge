"""Local LLM adapter."""

from __future__ import annotations

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class LocalLLMAdapter(MockAdapter):
    # TODO: embedding_model — local embedding via vector._simple_embedding hash

    def format_context(self, context: ContextPackage) -> str:
        return super().format_context(context)

    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str:
        return self.format_context(context)

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        # Mock by default; when llm_enabled=true placeholder for local LLM HTTP call
        # TODO: when local base_url set, call `httpx` against localhost:11434/v1
        return await super().complete(context, model_config)

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 4096
