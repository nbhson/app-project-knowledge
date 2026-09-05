"""Pydantic Settings with YAML + env overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitSourceConfig(BaseModel):
    repos: list[dict[str, Any]] = Field(default_factory=list)
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
    patterns: list[str] = Field(default_factory=lambda: ["*.md", "*.pdf"])


class SourceConfig(BaseModel):
    git: GitSourceConfig = Field(default_factory=GitSourceConfig)
    confluence: ConfluenceSourceConfig = Field(default_factory=ConfluenceSourceConfig)
    jira: JiraSourceConfig = Field(default_factory=JiraSourceConfig)
    documents: DocumentSourceConfig = Field(default_factory=DocumentSourceConfig)


class MetadataStoreConfig(BaseModel):
    provider: str = "sqlite"
    sqlite_path: str = "./data/pkh.db"
    url: str | None = None


class VectorStoreConfig(BaseModel):
    provider: str = "chroma"
    path: str = "./data/chroma"
    collection: str = "knowledge"
    embedding_model: str = "text-embedding-3-small"


class GraphStoreConfig(BaseModel):
    provider: str = "networkx"
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
            return cls()
        data = yaml.safe_load(p.read_text()) or {}
        # handle flat yaml keys
        return cls(**data)

    @classmethod
    def load(cls, yaml_path: str | Path | None = None) -> Settings:
        # try yaml_path, then config/settings.yaml, then env only
        candidates: list[Path] = []
        if yaml_path:
            candidates.append(Path(yaml_path))
        candidates.extend(
            [Path("config/settings.yaml"), Path("config.yaml"), Path("./settings.yaml")]
        )
        for c in candidates:
            if c.exists():
                return cls.from_yaml(c)
        return cls()


_settings: Settings | None = None


def get_settings(yaml_path: str | Path | None = None, reload: bool = False) -> Settings:
    global _settings
    if _settings is None or reload:
        if yaml_path:
            _settings = Settings.from_yaml(yaml_path)
        else:
            _settings = Settings.load()
        # env overrides already handled by BaseSettings
    return _settings
