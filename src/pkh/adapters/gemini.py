"""Gemini adapter."""

from pkh.adapters.mock import MockAdapter


class GeminiAdapter(MockAdapter):
    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 1000000
