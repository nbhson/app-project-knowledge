"""Metadata store - SQLAlchemy + SQLite."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    String,
    Text,
    create_engine,
    func,
    or_,
    select,
    update,
)
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
    __table_args__ = (
        Index("ix_knowledge_objects_title", "title"),
        Index("ix_knowledge_objects_content", "content"),
        Index("ix_knowledge_objects_lifecycle_state", "lifecycle_state"),
        Index("ix_knowledge_objects_entity_type", "entity_type"),
        Index("ix_knowledge_objects_object_type", "object_type"),
    )
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
                # parse fail -> keep as None (let SourceReference default handle it)
                # do not fallback to now() which would fabricate a timestamp
                sr["last_synced"] = None  # type: ignore[assignment]
                # if None is not desired, SourceReference will use default; pop invalid
                if sr["last_synced"] is None:
                    sr.pop("last_synced", None)
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


def _sqlite_url(sqlite_path: str) -> str:
    """Build SQLite URL that works on Windows absolute paths and POSIX."""
    p = Path(sqlite_path)
    try:
        posix = p.resolve().as_posix()
    except Exception:
        posix = str(sqlite_path).replace("\\", "/")
    return f"sqlite:///{posix}"


class MetadataStore:
    def __init__(self, sqlite_path: str = "./data/pkh.db", echo: bool = False):
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = sqlite_path
        self.engine = create_engine(_sqlite_url(sqlite_path), echo=echo, future=True)
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

    def get_many(self, ids: list[str]) -> list[KnowledgeObject]:
        if not ids:
            return []
        with Session(self.engine) as session:
            stmt = select(KnowledgeRow).where(KnowledgeRow.id.in_(ids))
            rows = session.execute(stmt).scalars().all()
            # preserve input order and skip missing
            row_map = {r.id: _row_to_ko(r) for r in rows}
            return [row_map[i] for i in ids if i in row_map]

    def query(
        self,
        filters: dict[str, Any] | None = None,
        lifecycle_states: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeObject]:
        filters = filters or {}
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
            if "ids" in filters and filters["ids"]:
                # batch fetch by ids - used by graph_search to avoid N+1
                ids = filters["ids"]
                if isinstance(ids, (list, tuple, set)):
                    stmt = stmt.where(KnowledgeRow.id.in_(list(ids)))
            if "entity_type" in filters:
                stmt = stmt.where(KnowledgeRow.entity_type == filters["entity_type"])
            if "object_type" in filters:
                stmt = stmt.where(KnowledgeRow.object_type == filters["object_type"])
            # Push text filter to DB via ILIKE before limit/offset (fixes pagination + O(N))
            if "query" in filters and filters["query"]:
                q = filters["query"]
                # escape % and _ for LIKE pattern — PHẢI khai báo escape="\\"
                # (trước đây chỉ chèn \%\_ nhưng không có ESCAPE clause → escaping
                # inert, % vẫn là wildcard sống).
                q_escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                pattern = f"%{q_escaped}%"
                stmt = stmt.where(
                    or_(
                        KnowledgeRow.title.ilike(pattern, escape="\\"),
                        KnowledgeRow.content.ilike(pattern, escape="\\"),
                        KnowledgeRow.description.ilike(pattern, escape="\\"),
                    )
                )
            # Push source_type filter to DB (JSON field -> LIKE on serialized JSON)
            # Primary filter in SQL, python post-filter kept only for precise JSON validation
            if "source_type" in filters:
                st = str(filters["source_type"])
                # JSON stored as TEXT; filter via LIKE for DB-side reduction.
                # Escape LIKE wildcards: user-controlled % / _ trước đây hoạt động
                # như wildcard → filter bypass / scan rộng bất ngờ.
                st_escaped = (
                    st.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    .replace('"', '""')
                )
                stmt = stmt.where(
                    KnowledgeRow.source_references.like(
                        f'%"source_type": "{st_escaped}"%', escape="\\"
                    )
                )
            # Apply limit/offset in DB (correct pagination)
            stmt = stmt.limit(limit).offset(offset)
            rows = session.execute(stmt).scalars().all()
            result = [_row_to_ko(r) for r in rows]
            # Python post-filter for JSON field precise check (remove LIKE false positives)
            if "source_type" in filters:
                st = filters["source_type"]
                result = [
                    k
                    for k in result
                    if any(sr.source_type.value == st for sr in k.source_references)
                ]
            return result

    def get_by_source(self, source_id: str) -> list[KnowledgeObject]:
        with Session(self.engine) as session:
            # DB-side filter via LIKE on JSON to avoid full scan O(N)
            sid_escaped = (
                source_id.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
                .replace('"', '""')
            )
            stmt = select(KnowledgeRow).where(
                KnowledgeRow.source_references.like(f'%"source_id": "{sid_escaped}"%', escape="\\")
            )
            rows = session.execute(stmt).scalars().all()
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
            return session.execute(select(func.count()).select_from(KnowledgeRow)).scalar_one()

    def claim_outbox(self, batch: int = 100) -> list[OutboxRow]:
        # Atomic claim với claim-token: UPDATE PENDING->CLAIMED kèm token ngẫu
        # nhiên trong payload, rồi SELECT theo token trong cùng transaction —
        # worker khác không bao giờ nhận trùng rows (trước đây SELECT PENDING
        # thuần: 2 worker chạy đồng thời claim TRÙNG rows, SQLite không có
        # FOR UPDATE SKIP LOCKED). Token lưu trong payload.claim — không cần
        # migrate schema.
        token = uuid.uuid4().hex
        with Session(self.engine) as session:
            session.execute(
                update(OutboxRow)
                .where(
                    OutboxRow.status == "PENDING",
                    OutboxRow.id.in_(
                        select(OutboxRow.id)
                        .where(OutboxRow.status == "PENDING")
                        .order_by(OutboxRow.created_at)
                        .limit(batch)
                    ),
                )
                .values(status="CLAIMED", payload={"claim": token})
            )
            rows = (
                session.execute(
                    select(OutboxRow).where(
                        OutboxRow.status == "CLAIMED",
                        OutboxRow.payload["claim"].as_string() == token,
                    )
                )
                .scalars()
                .all()
            )
            # Expunge trước commit: expire_on_commit mặc định True — commit
            # expire attributes của rows còn attached, caller truy cập attribute
            # sau khi session đóng → DetachedInstanceError.
            for r in rows:
                session.expunge(r)
            session.commit()
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
        from pkh.models.lifecycle import transition as lifecycle_transition

        with Session(self.engine) as session:
            row = session.get(KnowledgeRow, id)
            if row:
                # Validate transition via state machine before DB write
                ko = _row_to_ko(row)
                # transition() will raise LifecycleError if invalid
                lifecycle_transition(ko, new_state)
                # Only after validation, persist
                row.lifecycle_state = new_state.value
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
