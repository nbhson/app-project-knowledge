from pkh.adapters.base import ModelAdapter
from pkh.adapters.claude import ClaudeAdapter
from pkh.adapters.custom import CustomAdapter, OpenAICompatibleAdapter
from pkh.adapters.gemini import GeminiAdapter
from pkh.adapters.gpt import GPTAdapter
from pkh.adapters.local import LocalLLMAdapter
from pkh.adapters.mock import MockAdapter

ADAPTERS = {
    "mock": MockAdapter,
    "claude": ClaudeAdapter,
    "openai": GPTAdapter,
    "gpt": GPTAdapter,
    "gemini": GeminiAdapter,
    "local": LocalLLMAdapter,
    "custom": OpenAICompatibleAdapter,
    "openai-compatible": OpenAICompatibleAdapter,
    "openaicompatible": OpenAICompatibleAdapter,
    "openai_compatible": OpenAICompatibleAdapter,
}

_CUSTOM_ALIASES = {"custom", "openai-compatible", "openaicompatible", "openai_compatible"}


def get_adapter(
    name: str,
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    embedding_model: str | None = None,
    timeout_seconds: float | None = None,
):
    """Resolve adapter by name.

    - Builtins: mock/claude/gpt/gemini/local.
    - Custom OpenAI-compatible: "custom", "openai-compatible", "provider:<name>",
      or any key defined in settings adapters.providers.
    - Explicit base_url/model/api_key kwargs override settings (useful for CLI).
    """
    key = (name or "mock").strip()
    lowered = key.lower()
    has_override = any(
        v is not None for v in (base_url, model, api_key, embedding_model, timeout_seconds)
    )
    if lowered in _CUSTOM_ALIASES or lowered.startswith("provider:") or has_override:
        provider_name = key
        if lowered in _CUSTOM_ALIASES and not has_override:
            provider_name = key
        return OpenAICompatibleAdapter.from_settings(
            provider_name,
            base_url=base_url,
            model=model,
            api_key=api_key,
            embedding_model=embedding_model,
            timeout_seconds=timeout_seconds,
        )
    # named provider in settings (adapters.providers.<name>)
    try:
        from pkh.config.settings import get_settings

        providers = get_settings().adapters.providers
        if key in providers:
            return OpenAICompatibleAdapter.from_settings(
                key,
                base_url=base_url,
                model=model,
                api_key=api_key,
                embedding_model=embedding_model,
                timeout_seconds=timeout_seconds,
            )
    except Exception:
        pass
    cls = ADAPTERS.get(lowered, MockAdapter)
    return cls()


__all__ = [
    "ModelAdapter",
    "MockAdapter",
    "ClaudeAdapter",
    "GPTAdapter",
    "GeminiAdapter",
    "LocalLLMAdapter",
    "CustomAdapter",
    "OpenAICompatibleAdapter",
    "get_adapter",
    "ADAPTERS",
]
