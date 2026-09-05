"""Metadata store - SQLAlchemy + SQLite."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, String, Text, create_engine, select
from sqlalchemy.orm import Session, declarative_base

from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    LifecycleState,
    ObjectType,
    SourceReference,
)

Base = declarative_base()


class KnowledgeRow(Base):
    __tablename__ = "knowledge_objects"
    id = Column(String, primary_key=True)
    object_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    source_references = Column(JSON, nullable=False)  # stored as JSON list
    confidence = Column(Float, nullable=False)
    lifecycle_state = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    tags = Column(JSON, nullable=False)
    properties = Column(JSON, nullable=False)


class OutboxRow(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True)
    knowledge_id = Column(String, nullable=False)
    op = Column(String, nullable=False)  # UPSERT, DELETE
    status = Column(String, nullable=False)  # PENDING, DONE, FAILED
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
    error = Column(Text, nullable=True)


def _ko_to_row(ko: KnowledgeObject) -> KnowledgeRow:
    return KnowledgeRow(
        id=ko.id,
        object_type=ko.object_type.value,
        entity_type=ko.entity_type.value if ko.entity_type else None,
        title=ko.title,
        description=ko.description,
        content=ko.content,
        source_references=[sr.model_dump(mode="json") for sr in ko.source_references],
        confidence=ko.confidence,
        lifecycle_state=ko.lifecycle_state.value,
        created_at=ko.created_at,
        updated_at=ko.updated_at,
        tags=ko.tags,
        properties=ko.properties,
    )


def _row_to_ko(row: KnowledgeRow) -> KnowledgeObject:
    srs = []
    for sr in row.source_references or []:
        # handle datetime strings
        if "last_synced" in sr and isinstance(sr["last_synced"], str):
            try:
                sr["last_synced"] = datetime.fromisoformat(sr["last_synced"])
            except Exception:
                sr["last_synced"] = datetime.now(timezone.utc)
        srs.append(SourceReference(**sr))
    return KnowledgeObject(
        id=row.id,
        object_type=ObjectType(row.object_type),
        entity_type=EntityType(row.entity_type) if row.entity_type else None,
        title=row.title,
        description=row.description,
        content=row.content,
        source_references=srs,
        confidence=row.confidence,
        lifecycle_state=LifecycleState(row.lifecycle_state),
        created_at=row.created_at
        if row.created_at.tzinfo
        else row.created_at.replace(tzinfo=timezone.utc),
        updated_at=row.updated_at
        if row.updated_at.tzinfo
        else row.updated_at.replace(tzinfo=timezone.utc),
        tags=row.tags or [],
        properties=row.properties or {},
    )


class MetadataStore:
    def __init__(self, sqlite_path: str = "./data/pkh.db", echo: bool = False):
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = sqlite_path
        self.engine = create_engine(f"sqlite:///{sqlite_path}", echo=echo, future=True)
        Base.metadata.create_all(self.engine)

    def insert_many(self, kos: list[KnowledgeObject]) -> list[str]:
        ids: list[str] = []
        with Session(self.engine) as session:
            for ko in kos:
                row = _ko_to_row(ko)
                session.merge(row)  # upsert
                # outbox
                out = OutboxRow(
                    id=str(uuid.uuid4()),
                    knowledge_id=ko.id,
                    op="UPSERT",
                    status="PENDING",
                    payload={"id": ko.id},
                    created_at=datetime.now(timezone.utc),
                )
                session.add(out)
                ids.append(ko.id)
            session.commit()
        return ids

    def insert_one(self, ko: KnowledgeObject) -> str:
        return self.insert_many([ko])[0]

    def get(self, id: str) -> KnowledgeObject | None:
        with Session(self.engine) as session:
            row = session.get(KnowledgeRow, id)
            if not row:
                return None
            return _row_to_ko(row)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        lifecycle_states: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeObject]:
        filters = filters or {}
        has_text_query = bool(filters.get("query"))
        with Session(self.engine) as session:
            stmt = select(KnowledgeRow)
            if lifecycle_states:
                stmt = stmt.where(KnowledgeRow.lifecycle_state.in_(lifecycle_states))
            else:
                stmt = stmt.where(
                    KnowledgeRow.lifecycle_state.in_(
                        ["ACTIVE", "UPDATED", "EXTRACTED", "VALIDATING", "DISCOVERED"]
                    )
                )
            if "entity_type" in filters:
                stmt = stmt.where(KnowledgeRow.entity_type == filters["entity_type"])
            if "object_type" in filters:
                stmt = stmt.where(KnowledgeRow.object_type == filters["object_type"])
            # For text queries, fetch more rows before post-filtering to avoid truncation
            if has_text_query:
                # fetch without limit, apply filter in python, then slice
                rows = session.execute(stmt).scalars().all()
            else:
                if "source_type" in filters:
                    pass
                stmt = stmt.limit(limit).offset(offset)
                rows = session.execute(stmt).scalars().all()
            result = [_row_to_ko(r) for r in rows]
            if "source_type" in filters:
                st = filters["source_type"]
                result = [
                    k
                    for k in result
                    if any(sr.source_type.value == st for sr in k.source_references)
                ]
            if "query" in filters and filters["query"]:
                q = filters["query"].lower()
                result = [
                    k
                    for k in result
                    if q in k.title.lower()
                    or q in k.content.lower()
                    or q in (k.description or "").lower()
                ]
            # apply offset/limit after post-filter
            if has_text_query:
                result = result[offset : offset + limit]
            return result

    def get_by_source(self, source_id: str) -> list[KnowledgeObject]:
        with Session(self.engine) as session:
            rows = session.execute(select(KnowledgeRow)).scalars().all()
            result = []
            for r in rows:
                ko = _row_to_ko(r)
                if any(sr.source_id == source_id for sr in ko.source_references):
                    result.append(ko)
            return result

    def delete(self, id: str) -> None:
        with Session(self.engine) as session:
            row = session.get(KnowledgeRow, id)
            if row:
                session.delete(row)
                out = OutboxRow(
                    id=str(uuid.uuid4()),
                    knowledge_id=id,
                    op="DELETE",
                    status="PENDING",
                    payload={"id": id},
                    created_at=datetime.now(timezone.utc),
                )
                session.add(out)
                session.commit()

    def count(self) -> int:
        with Session(self.engine) as session:
            return session.query(KnowledgeRow).count()

    def claim_outbox(self, batch: int = 100) -> list[OutboxRow]:
        with Session(self.engine) as session:
            rows = (
                session.execute(select(OutboxRow).where(OutboxRow.status == "PENDING").limit(batch))
                .scalars()
                .all()
            )
            return rows

    def mark_outbox_done(self, outbox_id: str) -> None:
        with Session(self.engine) as session:
            row = session.get(OutboxRow, outbox_id)
            if row:
                row.status = "DONE"
                session.commit()

    def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        with Session(self.engine) as session:
            row = session.get(OutboxRow, outbox_id)
            if row:
                row.status = "FAILED"
                row.error = error
                session.commit()

    def all_knowledge(self, limit: int = 10000) -> list[KnowledgeObject]:
        with Session(self.engine) as session:
            rows = session.execute(select(KnowledgeRow).limit(limit)).scalars().all()
            return [_row_to_ko(r) for r in rows]

    def update_lifecycle(self, id: str, new_state: LifecycleState) -> None:
        with Session(self.engine) as session:
            row = session.get(KnowledgeRow, id)
            if row:
                row.lifecycle_state = new_state.value
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
