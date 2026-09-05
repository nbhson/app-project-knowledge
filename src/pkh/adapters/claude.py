"""Claude adapter."""

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class ClaudeAdapter(MockAdapter):
    def format_context(self, context: ContextPackage) -> str:
        base = super().format_context(context)
        return f"You are a project knowledge assistant. Answer using ONLY the knowledge below.\n\n{base}\n\n## Your Task\n{context.query}\n\nAnswer based only on the knowledge above. Cite sources when possible."

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 200000
