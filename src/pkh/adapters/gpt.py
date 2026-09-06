"""GPT adapter."""

from __future__ import annotations

import json

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class GPTAdapter(MockAdapter):
    def format_context(self, context: ContextPackage) -> str:
        # Standard OpenAI chat format with model + messages per fix-plan 2.7
        # Includes embedding_model TODO: vector._simple_embedding currently hash;
        # TODO: replace hash with text-embedding-3-small when OPENAI_API_KEY set
        # and settings.vector.embedding_model == "text-embedding-3-small"
        return json.dumps(
            {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a project knowledge assistant. "
                            "Answer using only provided knowledge."
                        ),
                    },
                    {"role": "user", "content": context.query},
                    {"role": "assistant", "content": super().format_context(context)},
                ],
                "knowledge_count": len(context.knowledge),
            },
            ensure_ascii=False,
        )

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
