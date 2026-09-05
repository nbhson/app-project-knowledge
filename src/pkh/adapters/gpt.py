"""GPT adapter."""

import json

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage


class GPTAdapter(MockAdapter):
    def format_context(self, context: ContextPackage) -> str:
        return json.dumps(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a project knowledge assistant. Answer using only provided knowledge.",
                    },
                    {"role": "user", "content": context.query},
                    {"role": "assistant", "content": super().format_context(context)},
                ],
                "knowledge_count": len(context.knowledge),
            },
            ensure_ascii=False,
        )

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 128000
