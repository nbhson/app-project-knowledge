"""Claude adapter."""

from __future__ import annotations

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class ClaudeAdapter(MockAdapter):
    # TODO: embedding_model wiring — vector._simple_embedding currently hash;
    # replace with text-embedding-3-small when OPENAI_API_KEY set and
    # settings.vector.embedding_model == "text-embedding-3-small"

    def format_context(self, context: ContextPackage) -> str:
        base = super().format_context(context)
        return (
            "You are a project knowledge assistant. "
            f"Answer using ONLY the knowledge below.\n\n{base}\n\n"
            f"## Your Task\n{context.query}\n\n"
            "Answer based only on the knowledge above. Cite sources when possible."
        )

    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str:
        return self.format_context(context)

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        # When llm_enabled=false (default per adr-004) use Mock behavior.
        # When true, placeholder for Anthropic SDK:
        # TODO: when ANTHROPIC_API_KEY set and llm_enabled=true,
        #   use `import anthropic; client.messages.create(model=..., messages=[...])`
        #   with format_context as system prompt. Keep mock fallback for tests.
        try:
            # check if real SDK should be used
            model_config = model_config or {}
            use_real = model_config.get("llm_enabled") is True
            if use_real:
                import anthropic  # type: ignore

                # placeholder: would call anthropic client here
                _ = anthropic  # avoid unused import
        except Exception:
            pass
        return await super().complete(context, model_config)

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 200000
