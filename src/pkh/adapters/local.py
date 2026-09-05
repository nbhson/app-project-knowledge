"""Local LLM adapter."""

from pkh.adapters.mock import MockAdapter


class LocalLLMAdapter(MockAdapter):
    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 4096
