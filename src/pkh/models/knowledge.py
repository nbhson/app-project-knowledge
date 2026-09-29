"""Core knowledge models: enums, SourceReference, KnowledgeObject."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LifecycleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    EXTRACTED = "EXTRACTED"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    UPDATED = "UPDATED"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class ObjectType(str, Enum):
    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"
    DECISION = "DECISION"
    RULE = "RULE"


class EntityType(str, Enum):
    REPOSITORY = "REPOSITORY"
    MODULE = "MODULE"
    PACKAGE = "PACKAGE"
    FILE = "FILE"
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    ENUM = "ENUM"
    TYPE = "TYPE"
    VARIABLE = "VARIABLE"
    EPIC = "EPIC"
    STORY = "STORY"
    TASK = "TASK"
    BUG = "BUG"
    DOCUMENT = "DOCUMENT"
    REQUIREMENT = "REQUIREMENT"
    DECISION = "DECISION"
    BUSINESS_RULE = "BUSINESS_RULE"
    API = "API"
    DATABASE = "DATABASE"
    SERVICE = "SERVICE"
    ENDPOINT = "ENDPOINT"

    # Legacy aliases (deprecated, keep for DB compat) — not counted in 23 canonical types
    # Use _missing_ to map old persisted values to canonical ones.

    @classmethod
    def _missing_(cls, value: object) -> EntityType | None:  # type: ignore[override]
        legacy_map = {
            "ADR": cls.DECISION,
            "API_SPEC": cls.API,
            "COMPONENT": cls.SERVICE,
            "INFRASTRUCTURE": cls.SERVICE,
        }
        if isinstance(value, str) and value in legacy_map:
            return legacy_map[value]
        return None


class RelationshipType(str, Enum):
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    CALLS = "CALLS"
    USES = "USES"
    OWNS = "OWNS"
    DOCUMENTS = "DOCUMENTS"
    REQUIRES = "REQUIRES"
    SUPERSEDES = "SUPERSEDES"
    RELATED_TO = "RELATED_TO"
    AFFECTS = "AFFECTS"
    PART_OF = "PART_OF"
    TRACES_TO = "TRACES_TO"
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS_IFACE = "IMPLEMENTS_IFACE"


class SourceType(str, Enum):
    GIT = "GIT"
    CONFLUENCE = "CONFLUENCE"
    JIRA = "JIRA"
    DOCUMENT = "DOCUMENT"
    API_SPEC = "API_SPEC"


PKH_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def deterministic_id(source_id: str, kind: str, name: str) -> str:
    """Deterministic UUID5 for dedup: same source+kind+name -> same id."""
    return str(uuid.uuid5(PKH_NAMESPACE, f"{source_id}:{kind}:{name}"))


_ALLOWED_URL_SCHEMES = (
    "http://",
    "https://",
    "git://",
    "file://",
    "confluence://",
    "jira://",
    "document://",
)


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    source_type: SourceType
    source_id: str = Field(..., min_length=1)
    url: str | None = None
    title: str | None = None
    last_synced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def url_must_be_safe(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if ".." in v:
            raise ValueError("url must not contain path traversal '..'")
        if "://" in v:
            low = v.lower()
            if not low.startswith(_ALLOWED_URL_SCHEMES) and not low.startswith("/"):
                # allow absolute paths and plain ids, but block unknown schemes
                # e.g. javascript:, data:, ftp: are rejected
                if ":" in v.split("/")[0]:
                    raise ValueError(f"unsupported url scheme in {v!r}")
        return v


class KnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    object_type: ObjectType
    entity_type: EntityType | None = None
    relationship_type: RelationshipType | None = None
    source_id: str | None = Field(default=None, description="Source entity KO id for RELATIONSHIP")
    target_id: str | None = Field(default=None, description="Target entity KO id for RELATIONSHIP")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    content: str = Field(..., min_length=1, max_length=50000)
    source_references: list[SourceReference] = Field(..., min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    lifecycle_state: LifecycleState = Field(default=LifecycleState.DISCOVERED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must be non-empty")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must be non-empty")
        return v

    @model_validator(mode="after")
    def validate_entity_type(self) -> KnowledgeObject:
        if self.object_type == ObjectType.ENTITY and self.entity_type is None:
            raise ValueError("entity_type is required when object_type is ENTITY")
        if self.object_type == ObjectType.RELATIONSHIP:
            # backfill typed fields from legacy properties for compat
            if self.relationship_type is None:
                raw = self.properties.get("rel_type") or self.properties.get("relationship_type")
                if raw:
                    try:
                        object.__setattr__(self, "relationship_type", RelationshipType(raw))
                    except Exception:
                        object.__setattr__(self, "relationship_type", RelationshipType.RELATED_TO)
                else:
                    object.__setattr__(self, "relationship_type", RelationshipType.RELATED_TO)
            if self.source_id is None and (
                self.properties.get("from") or self.properties.get("from_id")
            ):
                object.__setattr__(
                    self,
                    "source_id",
                    str(self.properties.get("from") or self.properties.get("from_id")),
                )
            if self.target_id is None and (
                self.properties.get("to") or self.properties.get("to_id")
            ):
                object.__setattr__(
                    self,
                    "target_id",
                    str(self.properties.get("to") or self.properties.get("to_id")),
                )
        # auto-touch updated_at on assignment is handled by validate_assignment;
        # ensure tz-aware datetimes
        for attr in ("created_at", "updated_at"):
            dt = getattr(self, attr, None)
            if isinstance(dt, datetime) and dt.tzinfo is None:
                object.__setattr__(self, attr, dt.replace(tzinfo=timezone.utc))
        return self
