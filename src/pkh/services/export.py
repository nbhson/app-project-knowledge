"""Export knowledge objects to portable formats (json / csv / markdown).

Round 2 feature: `pkh export` — make the stored corpus usable outside PKH
(reports, spreadsheets, docs-as-code pipelines) without direct DB access.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from typing import TextIO

from pkh.models.knowledge import KnowledgeObject
from pkh.utils.exceptions import ConfigurationError

EXPORT_FORMATS = ("json", "csv", "markdown")
# flatten the source_references list into these columns for csv/markdown
_SOURCE_COLUMNS = ("source_type", "source_id", "url")


def _first_source(ko: KnowledgeObject) -> dict:
    if ko.source_references:
        return ko.source_references[0].model_dump()
    return {}


def _flatten(ko: KnowledgeObject) -> dict[str, str]:
    src = _first_source(ko)
    return {
        "id": ko.id,
        "title": ko.title,
        "object_type": ko.object_type.value,
        "entity_type": ko.entity_type.value if ko.entity_type else "",
        "lifecycle_state": ko.lifecycle_state.value,
        "confidence": f"{ko.confidence:.2f}",
        "created_at": ko.created_at.isoformat(),
        "updated_at": ko.updated_at.isoformat(),
        "tags": ",".join(ko.tags),
        "source_type": str(src.get("source_type", "")),
        "source_id": str(src.get("source_id", "")),
        "source_url": str(src.get("url", "") or ""),
        "description": ko.description or "",
        "content": ko.content,
    }


def _to_json(kos: list[KnowledgeObject], out: TextIO) -> None:
    json.dump(
        [ko.model_dump(mode="json") for ko in kos],
        out,
        indent=2,
        ensure_ascii=False,
    )
    out.write("\n")


_CSV_COLUMNS = (
    "id",
    "title",
    "object_type",
    "entity_type",
    "lifecycle_state",
    "confidence",
    "created_at",
    "updated_at",
    "tags",
    "source_type",
    "source_id",
    "source_url",
    "description",
)


def _to_csv(kos: list[KnowledgeObject], out: TextIO) -> None:
    writer = csv.DictWriter(out, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for ko in kos:
        writer.writerow(_flatten(ko))


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _to_markdown(kos: list[KnowledgeObject], out: TextIO) -> None:
    out.write("# PKH Knowledge Export\n\n")
    out.write(f"Objects: {len(kos)}\n\n")
    out.write(
        "| Title | Type | State | Confidence | Source | Updated |\n|---|---|---|---|---|---|\n"
    )
    for ko in kos:
        f = _flatten(ko)
        out.write(
            f"| {_md_escape(f['title'][:80])} | {f['object_type']} | "
            f"{f['lifecycle_state']} | {f['confidence']} | "
            f"{_md_escape(f['source_type'])} | {f['updated_at'][:10]} |\n"
        )
    out.write("\n")
    # full records below the summary table
    for ko in kos:
        src = _first_source(ko)
        out.write(f"## {ko.title}\n\n")
        out.write(f"- **ID**: `{ko.id}`\n")
        out.write(f"- **Type**: {ko.object_type.value}")
        if ko.entity_type:
            out.write(f" / {ko.entity_type.value}")
        out.write("\n")
        out.write(f"- **Lifecycle**: {ko.lifecycle_state.value}\n")
        out.write(f"- **Confidence**: {ko.confidence:.2f}\n")
        if src.get("source_id"):
            out.write(f"- **Source**: {src.get('source_type', '')} `{src.get('source_id', '')}`\n")
        if ko.tags:
            out.write(f"- **Tags**: {', '.join(ko.tags)}\n")
        if ko.description:
            out.write(f"\n{ko.description}\n")
        excerpt = ko.content[:500]
        suffix = "\n\n*(truncated)*" if len(ko.content) > 500 else ""
        out.write(f"\n```\n{excerpt}{suffix}\n```\n\n")


_RENDERERS: dict[str, Callable[[list[KnowledgeObject], TextIO], None]] = {
    "json": _to_json,
    "csv": _to_csv,
    "markdown": _to_markdown,
}


def render_export(kos: list[KnowledgeObject], fmt: str, out: TextIO) -> None:
    """Render `kos` in the requested format to `out`.

    Raises ConfigurationError on an unknown format (callers map this to a
    clear user-facing error / exit code 2).
    """
    key = (fmt or "json").strip().lower()
    renderer = _RENDERERS.get(key)
    if renderer is None:
        raise ConfigurationError(
            f"unknown export format: {fmt!r} (supported: {', '.join(EXPORT_FORMATS)})"
        )
    renderer(kos, out)
