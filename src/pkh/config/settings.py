"""Pydantic Settings with YAML + env overrides."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pkh.utils.exceptions import ConfigurationError


class GitRepoConfig(BaseModel):
    url: str = "./"
    branch: str = "main"
    auth_type: Literal["none", "basic", "token", "ssh"] = "none"


class GitSourceConfig(BaseModel):
    repos: list[GitRepoConfig] = Field(default_factory=list)
    branch: str = "main"
    auth_type: Literal["none", "basic", "token", "ssh"] = "none"


class ConfluenceSourceConfig(BaseModel):
    url: str = ""
    spaces: list[str] = Field(default_factory=list)
    auth_type: Literal["none", "basic", "token"] = "none"


class JiraSourceConfig(BaseModel):
    url: str = ""
    projects: list[str] = Field(default_factory=list)
    auth_type: Literal["none", "basic", "token"] = "none"
    issue_types: list[str] = Field(default_factory=list)


class DocumentSourceConfig(BaseModel):
    paths: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=lambda: ["*.md", "*.pdf", "*.yaml", "*.json"])


class SourceConfig(BaseModel):
    git: GitSourceConfig = Field(default_factory=GitSourceConfig)
    confluence: ConfluenceSourceConfig = Field(default_factory=ConfluenceSourceConfig)
    jira: JiraSourceConfig = Field(default_factory=JiraSourceConfig)
    documents: DocumentSourceConfig = Field(default_factory=DocumentSourceConfig)


class MetadataStoreConfig(BaseModel):
    provider: Literal["sqlite", "postgresql"] = "sqlite"
    sqlite_path: str = "./data/pkh.db"
    url: str | None = None


class VectorStoreConfig(BaseModel):
    provider: Literal["chroma", "pgvector", "memory"] = "chroma"
    path: str = "./data/chroma"
    collection: str = "knowledge"
    embedding_model: str = "text-embedding-3-small"


class GraphStoreConfig(BaseModel):
    provider: Literal["networkx", "neo4j"] = "networkx"
    persist_path: str = "./data/graph.json"


class StorageConfig(BaseModel):
    metadata: MetadataStoreConfig = Field(default_factory=MetadataStoreConfig)
    vector: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    graph: GraphStoreConfig = Field(default_factory=GraphStoreConfig)


class FusionConfig(BaseModel):
    method: Literal["rrf", "weighted", "none"] = "rrf"
    k: int = Field(default=60, ge=1, le=1000)


class RerankerConfig(BaseModel):
    confidence_weight: float = 0.3
    lifecycle_weight: float = 0.2
    recency_weight: float = 0.1
    relevance_weight: float = 0.4


class RetrievalConfig(BaseModel):
    strategies: list[Literal["vector", "keyword", "graph"]] = Field(
        default_factory=lambda: ["vector", "keyword", "graph"],  # type: ignore[arg-type]
    )
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    weights_per_intent: dict[str, dict[str, float]] = Field(default_factory=dict)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)

    @field_validator("weights_per_intent")
    @classmethod
    def weights_must_sum_to_one(cls, v: dict) -> dict:
        for intent, weights in v.items():
            total = sum(weights.values())
            if weights and abs(total - 1.0) > 0.01:
                raise ValueError(f"weights for intent {intent} must sum to 1.0 (got {total})")
            for strat in weights:
                if strat not in ("vector", "keyword", "graph"):
                    raise ValueError(f"unknown strategy {strat} for intent {intent}")
        return v


class CustomProviderConfig(BaseModel):
    """OpenAI-compatible custom provider: base_url + model + api_key.

    Works with OpenAI, Azure OpenAI, OpenRouter, Ollama, vLLM, LM Studio,
    or any server exposing POST {base_url}/chat/completions and
    POST {base_url}/embeddings.
    """

    base_url: str = ""
    model: str = ""
    api_key: str | None = None
    embedding_model: str | None = None
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=128000)
    token_limit: int = Field(default=128000, ge=1)
    extra_headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("base_url")
    @classmethod
    def base_url_no_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/") if v else v


class AdapterConfig(BaseModel):
    default: str = "mock"
    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-sonnet-4"
    gemini_model: str = "gemini-pro"
    # Named custom providers: adapters.providers.<name> = {base_url, model, api_key, ...}
    # Select via adapters.default = "<name>" or "provider:<name>".
    providers: dict[str, CustomProviderConfig] = Field(default_factory=dict)
    # Shortcut for a single custom provider (equiv. providers["custom"]).
    custom_base_url: str = ""
    custom_model: str = ""
    custom_api_key: str | None = None
    custom_embedding_model: str | None = None

    def resolve_provider(self, name: str | None = None) -> CustomProviderConfig | None:
        """Return CustomProviderConfig for `name` (or default). None if not a custom provider."""
        key = (name or self.default or "").strip()
        if key.lower().startswith("provider:"):
            key = key.split(":", 1)[1].strip()
        lowered = key.lower()
        if lowered in ("custom", "openai-compatible", "openaicompatible", "openai_compatible"):
            if self.providers.get("custom"):
                return self.providers["custom"]
            if self.custom_base_url or self.custom_model:
                return CustomProviderConfig(
                    base_url=self.custom_base_url,
                    model=self.custom_model,
                    api_key=self.custom_api_key,
                    embedding_model=self.custom_embedding_model,
                )
            return CustomProviderConfig()
        if key and key in self.providers:
            return self.providers[key]
        return None


class ExtractionConfig(BaseModel):
    llm_enabled: bool = False
    llm_adapter: str = "mock"
    batch_size: int = 15
    cache_ttl_days: int = 7
    budget_per_run_tokens: int = 50000


class GovernanceConfig(BaseModel):
    rbac_enabled: bool = False
    audit_retention_days: int = 90
    audit_path: str = "./data/audit.jsonl"
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PKH_", env_nested_delimiter="__", extra="ignore")

    sources: SourceConfig = Field(default_factory=SourceConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    adapters: AdapterConfig = Field(default_factory=AdapterConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)

    config_file: str | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> Settings:
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Config YAML not found: {p}")
        data: dict[str, Any] = yaml.safe_load(p.read_text()) or {}
        # Ensure env vars override YAML (Pydantic Settings init would otherwise let YAML win)
        # Remove YAML keys that have corresponding PKH_ env var set.
        # Case-insensitive: PKH_SOURCES__GIT__REPOS, PKH_STORAGE__METADATA__SQLITE_PATH, etc.
        # Also support list index syntax is out of scope; env wins by dropping YAML leaf.
        for ek in list(os.environ.keys()):
            if not ek.startswith("PKH_"):
                continue
            # strip prefix, split on __, lowercase each part
            key_path = [part.lower() for part in ek[4:].split("__") if part]
            if not key_path:
                continue
            cur: Any = data
            found = True
            for part in key_path[:-1]:
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    found = False
                    break
            if found and isinstance(cur, dict):
                leaf = key_path[-1]
                if leaf in cur:
                    cur.pop(leaf)
        return cls(**data)

    @classmethod
    def load(cls, yaml_path: str | Path | None = None) -> Settings:
        # Respect PKH_CONFIG_FILE env var as highest priority
        env_cfg = os.getenv("PKH_CONFIG_FILE")
        if env_cfg:
            env_path = Path(env_cfg)
            if env_path.exists():
                return cls.from_yaml(env_path)
            raise ConfigurationError(f"PKH_CONFIG_FILE not found: {env_path}")
        candidates: list[Path] = []
        if yaml_path:
            candidates.append(Path(yaml_path))
        candidates.extend(
            [Path("config/settings.yaml"), Path("config.yaml"), Path("./settings.yaml")]
        )
        for c in candidates:
            if c.exists():
                return cls.from_yaml(c)
        # No YAML found: return env-only settings (not silent fallback for explicit path)
        if yaml_path is not None:
            raise ConfigurationError(f"Config YAML not found: {yaml_path}")
        return cls()


def resolve_provider_api_key(
    provider: CustomProviderConfig | None,
    *,
    explicit: str | None = None,
) -> str | None:
    """Resolve API key: explicit arg > provider.api_key > well-known env vars."""
    if explicit:
        return explicit
    if provider is not None and provider.api_key:
        return provider.api_key
    for env_name in (
        "PKH_ADAPTERS__CUSTOM_API_KEY",
        "PKH_CUSTOM_API_KEY",
        "CUSTOM_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "LLM_API_KEY",
    ):
        val = os.getenv(env_name)
        if val:
            return val
    return None


_settings: Settings | None = None
_settings_key: tuple[str | None, str | None] | None = None
_settings_lock = threading.Lock()


def get_settings(yaml_path: str | Path | None = None, reload: bool = False) -> Settings:
    global _settings, _settings_key
    # thread-safe singleton via lock (fix-plan 3.2)
    # key includes yaml_path + PKH_CONFIG_FILE to avoid test pollution
    env_cfg = os.getenv("PKH_CONFIG_FILE")
    key = (str(yaml_path) if yaml_path else None, env_cfg)
    with _settings_lock:
        if _settings is None or reload or _settings_key != key:
            if yaml_path:
                _settings = Settings.from_yaml(yaml_path)
            else:
                _settings = Settings.load()
            _settings_key = key
        return _settings


def reset_settings() -> None:
    """Test helper: clear singleton cache."""
    global _settings, _settings_key
    with _settings_lock:
        _settings = None
        _settings_key = None
