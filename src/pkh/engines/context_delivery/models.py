"""ContextPackage models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from pkh.models.knowledge import EntityType, LifecycleState, RelationshipType, SourceReference


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: EntityType | str
    title: str
    content: str
    confidence: float
    lifecycle_state: LifecycleState | str
    relevance_score: float = 0.0
    rank: int = 0
    sources: list[SourceReference] = Field(default_factory=list)


class RelationshipChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_id: str
    to_id: str
    type: RelationshipType | str
    confidence: float = 1.0


class SearchStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vector_results: int = 0
    keyword_results: int = 0
    graph_results: int = 0
    total_before_dedup: int = 0
    total_after_dedup: int = 0
    strategies_used: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    compression_log: list[dict] = Field(default_factory=list)


class ContextPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    knowledge: list[KnowledgeChunk]
    relationships: list[RelationshipChunk] = Field(default_factory=list)
    confidence: float
    sources: list[SourceReference]
    lifecycle_states: list[str]
    warnings: list[str] = Field(default_factory=list)
    intent: str = ""
    search_stats: SearchStats | None = None
    compression_ratio: float = 1.0
