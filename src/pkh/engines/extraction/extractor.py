"""Rule-based entity/relationship extractors."""

from __future__ import annotations

import re
import uuid

from pkh.engines.code_intelligence.parser import CodeKnowledgeOutput
from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import (
    EntityType,
    KnowledgeObject,
    ObjectType,
    RelationshipType,
    SourceReference,
    SourceType,
)


def _make_source_ref(item: RawItem) -> SourceReference:
    st = item.source_type
    try:
        source_type = SourceType(st)
    except Exception:
        source_type = SourceType.GIT if st == "GIT" else SourceType.DOCUMENT
    return SourceReference(
        source_type=source_type,
        source_id=item.item_id,
        title=item.title,
        extra=item.metadata,
    )


def extract_from_code(code_output: CodeKnowledgeOutput, item: RawItem) -> list[KnowledgeObject]:
    ref = _make_source_ref(item)
    kos: list[KnowledgeObject] = []

    kind_to_entity = {
        "CLASS": EntityType.CLASS,
        "FUNCTION": EntityType.FUNCTION,
        "METHOD": EntityType.METHOD,
        "INTERFACE": EntityType.INTERFACE,
        "ENUM": EntityType.ENUM,
        "TYPE": EntityType.TYPE,
        "VARIABLE": EntityType.VARIABLE,
    }

    for ent in code_output.entities:
        et = kind_to_entity.get(ent.kind, EntityType.FILE)
        # map METHOD -> METHOD still valid, else use mapping
        if ent.kind == "METHOD":
            et = EntityType.METHOD
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.ENTITY,
                entity_type=et,
                title=ent.name,
                description=ent.documentation or ent.signature,
                content=f"{ent.signature}\n{ent.documentation}\nFile: {ent.file_path}:{ent.line_start}-{ent.line_end}",
                source_references=[ref],
                confidence=1.0,
                properties={
                    "file_path": ent.file_path,
                    "line_start": ent.line_start,
                    "line_end": ent.line_end,
                    "signature": ent.signature,
                    "kind": ent.kind,
                },
            )
        )

    # file entity itself
    kos.append(
        KnowledgeObject(
            id=str(uuid.uuid4()),
            object_type=ObjectType.ENTITY,
            entity_type=EntityType.FILE,
            title=item.item_id,
            description=f"File {item.item_id}",
            content=item.content[:5000],
            source_references=[ref],
            confidence=1.0,
            properties={
                "language": item.metadata.get("language", ""),
                "size_bytes": len(item.content),
            },
        )
    )

    # relationships as KnowledgeObjects
    for rel in code_output.relationships:
        # relationships stored as RULE? Actually object_type RELATIONSHIP
        try:
            rt = RelationshipType(rel.type)
        except Exception:
            rt = RelationshipType.RELATED_TO
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.RELATIONSHIP,
                title=f"{rel.from_entity} {rt.value} {rel.to_entity}",
                description=f"{rel.type} from {rel.from_entity} to {rel.to_entity}",
                content=f"{rel.from_entity} --{rel.type}--> {rel.to_entity}",
                source_references=[ref],
                confidence=rel.confidence,
                properties={"from": rel.from_entity, "to": rel.to_entity, "rel_type": rel.type},
            )
        )
    return kos


def extract_from_document(item: RawItem) -> list[KnowledgeObject]:
    ref = _make_source_ref(item)
    kos: list[KnowledgeObject] = []
    content = item.content

    # ADR detection
    is_adr = bool(
        re.search(r"ADR[-\s]?\d+", item.title, re.I)
        or re.search(r"Decision|ADR", content[:500], re.I)
    )
    if is_adr and ("Consequences" in content or "Context" in content or "Decision" in content):
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.DECISION,
                title=item.title,
                description="Architecture Decision Record",
                content=content[:8000],
                source_references=[ref],
                confidence=0.9,
                properties={"decision_type": "ADR"},
            )
        )

    # Requirement extraction from JIRA types handled elsewhere, but detect epics/stories headings
    # Extract headings
    headings = re.findall(r"^#+\s+(.+)", content, re.M)
    for h in headings[:10]:
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.ENTITY,
                entity_type=EntityType.DOCUMENT,
                title=h.strip(),
                description=f"Section: {h.strip()} in {item.title}",
                content=h.strip(),
                source_references=[ref],
                confidence=0.7,
                properties={"section": h.strip()},
            )
        )

    # Business rule detection
    rules = re.findall(r"(must|should|cannot|required|shall)\s+[^\n\.]{10,120}", content, re.I)
    for r in rules[:5]:
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.RULE,
                title=r.strip()[:80],
                description="Business rule",
                content=r.strip(),
                source_references=[ref],
                confidence=0.6,
                properties={"rule_type": "business"},
            )
        )

    # If no ADR/headings, still create a document entity
    if not kos:
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.ENTITY,
                entity_type=EntityType.DOCUMENT,
                title=item.title,
                description=item.title,
                content=content[:8000],
                source_references=[ref],
                confidence=0.7,
            )
        )
    else:
        # add base doc entity too if not already
        has_doc = any(k.entity_type == EntityType.DOCUMENT and k.title == item.title for k in kos)
        if not has_doc:
            kos.append(
                KnowledgeObject(
                    id=str(uuid.uuid4()),
                    object_type=ObjectType.ENTITY,
                    entity_type=EntityType.DOCUMENT,
                    title=item.title,
                    description=item.title,
                    content=content[:8000],
                    source_references=[ref],
                    confidence=0.8,
                )
            )

    # Trace references: JIRA-123, ADR-001
    jira_refs = re.findall(r"[A-Z]+-\d+", content)
    for j in set(jira_refs[:5]):
        kos.append(
            KnowledgeObject(
                id=str(uuid.uuid4()),
                object_type=ObjectType.RELATIONSHIP,
                title=f"{item.title} TRACES_TO {j}",
                description=f"References {j}",
                content=f"{item.title} traces to {j}",
                source_references=[ref],
                confidence=0.8,
                properties={"from": item.item_id, "to": j, "rel_type": "TRACES_TO"},
            )
        )

    return kos


def extract_from_jira(item: RawItem) -> list[KnowledgeObject]:
    ref = _make_source_ref(item)
    issue_type = item.metadata.get("issue_type", "TASK")
    map_type = {
        "Epic": EntityType.EPIC,
        "Story": EntityType.STORY,
        "Task": EntityType.TASK,
        "Bug": EntityType.BUG,
    }
    et = map_type.get(issue_type, EntityType.REQUIREMENT)
    return [
        KnowledgeObject(
            id=str(uuid.uuid4()),
            object_type=ObjectType.ENTITY,
            entity_type=et,
            title=item.title or item.item_id,
            description=item.content[:500],
            content=item.content[:8000] or item.title,
            source_references=[ref],
            confidence=0.95,
            properties={"issue_type": issue_type, "status": item.metadata.get("status", "")},
        )
    ]
