"""Pydantic Settings with YAML + env overrides."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pkh.utils.exceptions import ConfigurationError


class GitRepoConfig(BaseModel):
    url: str = "./"
    branch: str = "main"
    auth_type: str = "none"


class GitSourceConfig(BaseModel):
    repos: list[GitRepoConfig] = Field(default_factory=list)
    branch: str = "main"
    auth_type: str = "none"


class ConfluenceSourceConfig(BaseModel):
    url: str = ""
    spaces: list[str] = Field(default_factory=list)
    auth_type: str = "none"


class JiraSourceConfig(BaseModel):
    url: str = ""
    projects: list[str] = Field(default_factory=list)
    auth_type: str = "none"
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
    method: str = "rrf"
    k: int = 60


class RerankerConfig(BaseModel):
    confidence_weight: float = 0.3
    lifecycle_weight: float = 0.2
    recency_weight: float = 0.1
    relevance_weight: float = 0.4


class RetrievalConfig(BaseModel):
    strategies: list[str] = Field(default_factory=lambda: ["vector", "keyword", "graph"])
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    weights_per_intent: dict[str, dict[str, float]] = Field(default_factory=dict)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)


class AdapterConfig(BaseModel):
    default: str = "mock"
    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-sonnet-4"
    gemini_model: str = "gemini-pro"


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
        # Remove YAML keys that have corresponding PKH_ env var set
        for ek in list(os.environ.keys()):
            if not ek.startswith("PKH_"):
                continue
            key_path = ek[4:].lower().split("__")
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


_settings: Settings | None = None
_settings_lock = threading.Lock()


def get_settings(yaml_path: str | Path | None = None, reload: bool = False) -> Settings:
    global _settings
    # thread-safe singleton via lock (fix-plan 3.2)
    with _settings_lock:
        if _settings is None or reload:
            if yaml_path:
                _settings = Settings.from_yaml(yaml_path)
            else:
                _settings = Settings.load()
        return _settings
