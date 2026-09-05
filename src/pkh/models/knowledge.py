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
    REQUIREMENT = "REQUIREMENT"
    ADR = "ADR"
    DOCUMENT = "DOCUMENT"
    API_SPEC = "API_SPEC"
    ENDPOINT = "ENDPOINT"
    COMPONENT = "COMPONENT"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    INFRASTRUCTURE = "INFRASTRUCTURE"


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


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    source_type: SourceType
    source_id: str = Field(..., min_length=1)
    url: str | None = None
    title: str | None = None
    last_synced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, Any] = Field(default_factory=dict)


class KnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    object_type: ObjectType
    entity_type: EntityType | None = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    content: str = Field(..., min_length=1)
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
        return self
