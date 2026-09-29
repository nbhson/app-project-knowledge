"""GPT adapter."""

from __future__ import annotations

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class GPTAdapter(MockAdapter):
    def format_context(self, context: ContextPackage) -> str:
        # Human-readable like other adapters; structured chat payload is
        # available via format_messages() for real OpenAI calls.
        return super().format_context(context)

    def format_messages(self, context: ContextPackage) -> list[dict]:
        return [
            {
                "role": "system",
                "content": (
                    "You are a project knowledge assistant. Answer using only provided knowledge."
                ),
            },
            {"role": "user", "content": context.query},
            {"role": "assistant", "content": super().format_context(context)},
        ]

    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str:
        return self.format_context(context)

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        # Mock by default per adr-004 (llm_enabled=false).
        # When llm_enabled=true, placeholder for OpenAI SDK:
        # TODO: when OPENAI_API_KEY set, use `import openai; openai.chat.completions.create(...)`
        try:
            model_config = model_config or {}
            use_real = model_config.get("llm_enabled") is True
            if use_real:
                import openai  # type: ignore

                _ = openai
        except Exception:
            pass
        return await super().complete(context, model_config)

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 128000
