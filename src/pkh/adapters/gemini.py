"""Gemini adapter."""

from __future__ import annotations

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class GeminiAdapter(MockAdapter):
    # TODO: embedding_model — see vector._simple_embedding hash placeholder

    def format_context(self, context: ContextPackage) -> str:
        # Gemini uses text with examples; delegate to Mock format but keep own method
        return super().format_context(context)

    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str:
        return self.format_context(context)

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        # Mock by default; when llm_enabled=true placeholder for Google GenAI SDK
        # TODO: when GOOGLE_API_KEY set, use `import google.generativeai`
        try:
            model_config = model_config or {}
            use_real = model_config.get("llm_enabled") is True
            if use_real:
                import importlib.util

                _ = importlib.util.find_spec("google.generativeai")
        except Exception:
            pass
        return await super().complete(context, model_config)

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 1000000
