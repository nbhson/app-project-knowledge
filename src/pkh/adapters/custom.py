"""Custom OpenAI-compatible provider: base_url + model + api_key. No mock.

Works with OpenAI, Azure OpenAI (via base_url), OpenRouter, Ollama,
vLLM, LM Studio, or any server exposing:
  POST {base_url}/chat/completions
  POST {base_url}/embeddings
"""

from __future__ import annotations

import os
from typing import Any

from pkh.adapters.mock import MockAdapter
from pkh.engines.context_delivery.models import ContextPackage
from pkh.utils.exceptions import AdapterError, ConfigurationError
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


def _strip_trailing_slash(url: str) -> str:
    return url.rstrip("/") if url else url


class OpenAICompatibleAdapter(MockAdapter):
    """Real HTTP adapter. Raises AdapterError on failure (never silently mocks)."""

    def __init__(
        self,
        base_url: str = "",
        model: str = "",
        api_key: str | None = None,
        embedding_model: str | None = None,
        timeout_seconds: float = 60.0,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        token_limit: int = 128000,
        extra_headers: dict[str, str] | None = None,
    ):
        self.base_url = _strip_trailing_slash(base_url or os.getenv("PKH_CUSTOM_BASE_URL", ""))
        self.model = model or os.getenv("PKH_CUSTOM_MODEL", "")
        self.api_key = api_key or os.getenv("PKH_CUSTOM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.embedding_model = embedding_model or os.getenv("PKH_CUSTOM_EMBEDDING_MODEL")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._token_limit = token_limit
        self.extra_headers = dict(extra_headers or {})

    @classmethod
    def from_settings(
        cls,
        provider_name: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        embedding_model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> OpenAICompatibleAdapter:
        """Build from settings providers + explicit overrides + env."""
        from pkh.config.settings import get_settings, resolve_provider_api_key

        settings = get_settings()
        provider = settings.adapters.resolve_provider(provider_name or settings.adapters.default)
        if provider is None:
            # default provider entry missing -> fall back to shortcut fields
            base = base_url or settings.adapters.custom_base_url
            mdl = model or settings.adapters.custom_model
            key = api_key or settings.adapters.custom_api_key
            emb = embedding_model or settings.adapters.custom_embedding_model
            return cls(
                base_url=base,
                model=mdl,
                api_key=resolve_provider_api_key(None, explicit=key),
                embedding_model=emb,
                timeout_seconds=timeout_seconds or 60.0,
            )
        return cls(
            base_url=base_url or provider.base_url,
            model=model or provider.model,
            api_key=resolve_provider_api_key(provider, explicit=api_key),
            embedding_model=embedding_model or provider.embedding_model,
            timeout_seconds=timeout_seconds or provider.timeout_seconds,
            temperature=provider.temperature,
            max_tokens=provider.max_tokens,
            token_limit=provider.token_limit,
            extra_headers=provider.extra_headers,
        )

    def _require_config(self, *, need_embeddings: bool = False) -> None:
        if not self.base_url:
            raise ConfigurationError(
                "Custom provider base_url is missing. "
                "Set adapters.providers.<name>.base_url or adapters.custom_base_url."
            )
        if not self.model:
            raise ConfigurationError(
                "Custom provider model is missing. Set adapters.providers.<name>.model "
                "or adapters.custom_model (env PKH_CUSTOM_MODEL)."
            )
        if need_embeddings and not self.embedding_model:
            raise ConfigurationError(
                "Custom provider embedding_model is missing. Set "
                "adapters.providers.<name>.embedding_model to use vector embeddings."
            )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    def format_messages(self, context: ContextPackage) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are a project knowledge assistant. "
                    "Answer using ONLY the provided knowledge. Cite sources when possible."
                ),
            },
            {"role": "user", "content": self.format_context(context)},
        ]

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
        except Exception as e:
            raise AdapterError(f"Custom provider request failed: {e}") from e
        if resp.status_code != 200:
            raise AdapterError(
                f"Custom provider returned {resp.status_code}: {resp.text[:500]}",
                details={"status": resp.status_code, "url": url},
            )
        try:
            data = resp.json()
        except Exception as e:
            raise AdapterError(f"Custom provider returned non-JSON: {resp.text[:500]}") from e
        if isinstance(data, dict) and data.get("error"):
            raise AdapterError(f"Custom provider error: {data['error']}")
        return data if isinstance(data, dict) else {"data": data}

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        self._require_config()
        cfg = model_config or {}
        model = str(cfg.get("model") or self.model)
        temperature = float(cfg.get("temperature", self.temperature))
        max_tokens = int(cfg.get("max_tokens", self.max_tokens))
        payload = {
            "model": model,
            "messages": self.format_messages(context),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # allow extra OpenAI params passthrough (top_p, stop, ...), excluding internal keys
        for key in ("top_p", "stop", "presence_penalty", "frequency_penalty", "seed"):
            if key in cfg:
                payload[key] = cfg[key]
        data = await self._post_json(f"{self.base_url}/chat/completions", payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise AdapterError(f"Custom provider bad chat response: {str(data)[:500]}") from e
        if content is None:
            raise AdapterError("Custom provider returned empty content")
        if isinstance(content, list):
            # some providers return content blocks
            parts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
            return "".join(parts).strip()
        text = str(content).strip()
        if not text:
            raise AdapterError("Custom provider returned empty content")
        return text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._require_config(need_embeddings=True)
        assert self.embedding_model is not None
        payload = {"model": self.embedding_model, "input": texts}
        data = await self._post_json(f"{self.base_url}/embeddings", payload)
        try:
            items = sorted(data["data"], key=lambda d: d.get("index", 0))
            return [list(item["embedding"]) for item in items]
        except Exception as e:
            raise AdapterError(f"Custom provider bad embeddings response: {str(data)[:500]}") from e

    async def enrich(self, content: str) -> list:
        # Extraction pipeline hook: no auto-enrichment for generic providers
        # (keeps behavior explicit; override per use-case if needed).
        _ = content
        return []

    def get_token_limit(self, model_config: dict | None = None) -> int:
        if model_config and model_config.get("token_limit"):
            try:
                return int(model_config["token_limit"])
            except Exception:
                pass
        return self._token_limit


# Backwards-friendly alias
CustomAdapter = OpenAICompatibleAdapter
