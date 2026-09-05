from pkh.adapters.base import ModelAdapter
from pkh.adapters.claude import ClaudeAdapter
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
}


def get_adapter(name: str):
    cls = ADAPTERS.get(name.lower(), MockAdapter)
    return cls()


__all__ = [
    "ModelAdapter",
    "MockAdapter",
    "ClaudeAdapter",
    "GPTAdapter",
    "GeminiAdapter",
    "LocalLLMAdapter",
    "get_adapter",
    "ADAPTERS",
]
