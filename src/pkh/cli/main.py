"""PKH CLI — Typer + Rich.

Round 2: shared ingest/store services (no duplicated pipeline), global
--verbose/--quiet/--json/--config flags, consistent exit codes
(0 = ok, 1 = runtime failure, 2 = configuration error), progress feedback,
and new `pkh export` / `pkh doctor` commands.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from pkh.adapters import get_adapter
from pkh.adapters.base import ModelAdapter
from pkh.config.settings import Settings, get_settings
from pkh.governance.audit import AuditLog
from pkh.models.knowledge import EntityType, LifecycleState, ObjectType
from pkh.services.doctor import run_doctor
from pkh.services.export import EXPORT_FORMATS, render_export
from pkh.services.ingest import IngestOutcome, ingest_source
from pkh.services.query import run_query_pipeline
from pkh.services.runtime import SharedStore
from pkh.storage.unified import KnowledgeStore
from pkh.utils.exceptions import AdapterError, ConfigurationError
from pkh.utils.logging import get_logger, setup_logging

app = typer.Typer(
    help="Project Knowledge Harness — ingest, query, export and audit project knowledge.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()
err_console = Console(stderr=True)

logger = get_logger(__name__)

# CLI singleton per process, shared implementation with the API (round 2)
_shared_store = SharedStore()


def get_store() -> KnowledgeStore:
    return _shared_store.get()


def _settings_or_exit() -> Settings:
    """Load settings; map configuration problems to exit code 2."""
    try:
        return get_settings()
    except ConfigurationError as e:
        err_console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=2) from e


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
    quiet: bool = typer.Option(False, "--quiet", help="Only warnings and errors"),
    json_logs: bool = typer.Option(
        False, "--json", help="Emit structured JSON logs (machine-readable)"
    ),
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to settings YAML (overrides PKH_CONFIG_FILE)"),
    ] = None,
):
    """Project Knowledge Harness — continuous, connected project knowledge."""
    if config is not None:
        cfg = config.expanduser()
        if not cfg.exists():
            err_console.print(f"[red]Config file not found: {cfg}[/red]")
            raise typer.Exit(code=2)
        # PKH_CONFIG_FILE is the single override point consumed everywhere
        # (Settings.load, SharedStore, API) — reuse it instead of a CLI-only path.
        os.environ["PKH_CONFIG_FILE"] = str(cfg.resolve())
    setup_logging(verbose=verbose, quiet=quiet, fmt="json" if json_logs else "console")
    ctx.obj = {"json": json_logs}


def _resolve_sources(settings: Settings, source: str | None, sources: str | None) -> list[str]:
    """CLI flags -> source URL list (falls back to configured git repos)."""
    src_list: list[str] = []
    if sources:
        src_list.extend([s.strip() for s in sources.split(",") if s.strip()])
    if source:
        src_list.append(source)
    if not src_list:
        if settings.sources.git.repos:
            for r in settings.sources.git.repos:
                # repos are typed GitRepoConfig; handle legacy dict for safety
                if isinstance(r, dict):
                    url = r.get("url", "./")
                else:
                    url = getattr(r, "url", "./")
                src_list.append(f"git://{url}")
        else:
            src_list = ["git://./"]
    return src_list


async def _run_ingest(src_list: list[str], settings: Settings) -> None:
    """Shared ingest runner: progress feedback + per-source results + exit codes."""
    store = get_store()
    total_kos = 0
    failures: list[IngestOutcome] = []
    for src in src_list:
        console.print(f"[cyan]→[/cyan] Ingesting [bold]{src}[/bold]")
        try:
            outcome = await ingest_source(
                store,
                src,
                settings,
                reason="cli-ingest",
                on_progress=lambda d: console.print(f"    [dim]· {d}[/dim]"),
            )
        except ConfigurationError as e:
            err_console.print(f"[red]Configuration error:[/red] {e}")
            raise typer.Exit(code=2) from e
        if outcome.ok:
            total_kos += outcome.kos_extracted
            console.print(
                f"    [green]✓ {outcome.kos_extracted} knowledge objects "
                f"from {outcome.items_collected} raw items[/green]"
            )
            if outcome.transition_failures:
                console.print(
                    f"    [yellow]⚠ {outcome.transition_failures} lifecycle transition(s) "
                    "kept in original state[/yellow]"
                )
        else:
            failures.append(outcome)
            console.print(f"    [red]✗ failed: {outcome.error}[/red]")
    if failures:
        console.print(f"[bold red]{len(failures)} of {len(src_list)} source(s) failed:[/bold red]")
        for o in failures:
            console.print(f"  [red]✗ {o.source}: {o.error}[/red]")
    console.print(f"[bold green]Ingest done: {total_kos} knowledge objects[/bold green]")
    audit = AuditLog()
    audit.log(
        "ingest",
        resource=",".join(src_list),
        details={"count": total_kos, "failed": len(failures)},
    )
    if failures:
        raise typer.Exit(code=1)


def _resolve_cli_adapter(
    settings: Settings,
    provider: str | None,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
) -> ModelAdapter:
    """Resolve adapter with CLI overrides (explicit flags win over settings/env)."""
    name = provider or settings.adapters.default
    key = api_key or os.getenv("PKH_CUSTOM_API_KEY") or os.getenv("OPENAI_API_KEY")
    return get_adapter(
        name,
        base_url=base_url,
        model=model,
        api_key=key,
    )


@app.command()
def init(
    path: str = typer.Option(".", help="Path to init"),
    force: bool = typer.Option(False, help="Overwrite existing"),
):
    """Scaffold a settings YAML."""
    dest = Path(path) / "config" / "settings.yaml"
    # resolve example relative to package root (robust to cwd)
    candidates = [
        Path(__file__).resolve().parents[4] / "config" / "settings.yaml.example",
        Path("config/settings.yaml.example"),
    ]
    example = next((c for c in candidates if c.exists()), candidates[-1])
    if dest.exists() and not force:
        console.print(f"[yellow]Already exists: {dest} (use --force to overwrite)[/yellow]")
        raise typer.Exit(code=1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if example.exists():
        dest.write_text(example.read_text())
        console.print(f"[green]✓ Created {dest} from example[/green]")
    else:
        dest.write_text("# PKH settings\nstorage:\n  metadata:\n    sqlite_path: ./data/pkh.db\n")
        console.print(f"[green]✓ Created {dest}[/green]")
    console.print(f"[dim]Edit {dest} to configure sources[/dim]")


@app.command()
def ingest(
    source: str | None = typer.Option(
        None, "--source", help="Source URL like git://./path or confluence://SPACE"
    ),
    sources: str | None = typer.Option(
        None, "--sources", help="Comma-separated sources (mixed schemes allowed)"
    ),
):
    """Ingest knowledge from sources (git://, confluence://, jira://, document://)."""
    settings = _settings_or_exit()
    src_list = _resolve_sources(settings, source, sources)
    asyncio.run(_run_ingest(src_list, settings))


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural language query"),
    top_k: int = typer.Option(5, help="Top K results"),
    show_context: bool = typer.Option(False, help="Show raw context package"),
    provider: str | None = typer.Option(
        None, "--provider", help="LLM provider: mock/custom/<name in adapters.providers>"
    ),
    base_url: str | None = typer.Option(None, "--base-url", help="Custom provider base URL"),
    model: str | None = typer.Option(None, "--model", help="Custom provider model"),
    api_key: str | None = typer.Option(
        None, "--api-key", help="Custom provider API key (or env PKH_CUSTOM_API_KEY)"
    ),
):
    """Ask a natural-language question over the ingested knowledge."""
    settings = _settings_or_exit()

    async def _run():
        store = get_store()
        package, search_stats, intent = await run_query_pipeline(store, question, top_k=top_k)
        console.print(f"[dim]Intent: {intent.value}[/dim]")

        try:
            adapter = _resolve_cli_adapter(settings, provider, base_url, model, api_key)
            answer = await adapter.complete(package)
        except ConfigurationError as e:
            console.print(f"[red]Provider not configured:[/red] {e}")
            raise typer.Exit(code=2) from e
        except AdapterError as e:
            console.print(f"[red]Provider request failed:[/red] {e}")
            raise typer.Exit(code=1) from e

        console.print("\n[bold]Answer:[/bold]")
        console.print(answer)
        console.print("\n[dim]Sources:[/dim]")
        for s in package.sources[:5]:
            console.print(f"  - {s.source_type.value}: {s.source_id} {s.url or ''}")
        console.print(
            f"\n[dim]Confidence: {package.confidence:.2f} | "
            f"Intent: {package.intent} | Warnings: {package.warnings}[/dim]"
        )
        console.print(
            f"[dim]Latency: {search_stats.latency_ms:.0f}ms | "
            f"Results: {len(package.knowledge)}[/dim]"
        )

        if show_context:
            console.print("\n[bold]Context JSON:[/bold]")
            console.print_json(
                json.dumps(package.model_dump(mode="json"), indent=2, ensure_ascii=False)
            )

        audit = AuditLog()
        audit.log("query", resource=question, details={"intent": intent.value})

    try:
        asyncio.run(_run())
    except ConfigurationError as e:
        err_console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=2) from e


@app.command()
def context(
    query: str = typer.Option(..., "--query", help="Query to get context for"),
    top_k: int = typer.Option(5, help="Top K"),
    provider: str | None = typer.Option(
        None, "--provider", help="LLM provider for answer (default: context only)"
    ),
    model: str | None = typer.Option(None, "--model", help="Custom provider model override"),
):
    """Get the raw ContextPackage JSON (no LLM unless --provider is given)."""
    settings = _settings_or_exit()

    async def _run():
        store = get_store()
        package, _, intent = await run_query_pipeline(store, query, top_k=top_k)
        if provider or model:
            try:
                adapter = _resolve_cli_adapter(settings, provider, None, model, None)
                answer = await adapter.complete(package)
                console.print(f"[bold]Answer ({provider or settings.adapters.default}):[/bold]")
                console.print(answer)
            except ConfigurationError as e:
                err_console.print(f"[red]Provider not configured:[/red] {e}")
                raise typer.Exit(code=2) from e
            except AdapterError as e:
                err_console.print(f"[red]Provider request failed:[/red] {e}")
                raise typer.Exit(code=1) from e
        console.print_json(
            json.dumps(package.model_dump(mode="json"), indent=2, ensure_ascii=False)
        )

    asyncio.run(_run())


@app.command()
def graph(
    entity: str = typer.Option(..., "--entity", help="Entity name or ID"),
    depth: int = typer.Option(2, help="Traversal depth (1-5)"),
):
    """Explore the knowledge graph around an entity."""
    _settings_or_exit()
    store = get_store()
    depth = max(1, min(int(depth), 5))

    # find entity by name — score all candidates, pick best title match
    kos = store.metadata.query(filters={"query": entity}, limit=5)
    if not kos:
        console.print(f"[red]Entity not found:[/red] {entity}")
        raise typer.Exit(code=1)
    # prefer exact title match, else first
    target = next((k for k in kos if k.title.lower() == entity.lower()), kos[0])
    console.print(f"[cyan]Entity:[/cyan] {target.title} ({target.id}) type={target.entity_type}")
    neighbors = store.graph.get_neighbors(target.id, max_depth=depth)
    console.print(f"[dim]Neighbors (depth={depth}): {len(neighbors)}[/dim]")
    if neighbors:
        table = Table(title="Graph Neighbors")
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Type")
        for nid in neighbors[:20]:
            ko = store.metadata.get(nid)
            if ko:
                table.add_row(
                    ko.id[:8],
                    ko.title,
                    ko.entity_type.value if ko.entity_type else ko.object_type.value,
                )
            else:
                table.add_row(nid[:8], nid, "UNKNOWN")
        console.print(table)
    else:
        console.print("[yellow]No neighbors found[/yellow]")

    # ascii graph
    try:
        if neighbors:
            console.print("\n[dim]Edges:[/dim]")
            for nid in neighbors[:10]:
                path = store.graph.shortest_path(target.id, nid)
                if path:
                    console.print(f"  {' -> '.join(p[:8] for p in path)}")
    except Exception as e:
        console.print(f"[red]Graph error: {e}[/red]")


@app.command()
def status():
    """Show store component counts and recent audit activity."""
    _settings_or_exit()
    store = get_store()

    async def _collect():
        return await store.health_check()

    hc = asyncio.run(_collect())
    table = Table(title="PKH Status")
    table.add_column("Component")
    table.add_column("Count")
    table.add_row("Metadata (SQLite)", str(hc.get("metadata_count", 0)))
    table.add_row("Vector", str(hc.get("vector_count", 0)))
    table.add_row("Graph Nodes", str(hc.get("graph_nodes", 0)))
    table.add_row("Graph Edges", str(hc.get("graph_edges", 0)))
    console.print(table)
    audit = AuditLog()
    entries = audit.list(limit=5)
    console.print(f"[dim]Recent audit entries: {len(entries)}[/dim]")
    for e in entries:
        console.print(f"  {e.get('timestamp')} {e.get('action')} {e.get('resource')}")


@app.command()
def audit(
    limit: int = typer.Option(20, help="Number of entries to show"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify the hash chain"),
):
    """View the audit log (most recent first) and verify its hash chain."""
    al = AuditLog()
    entries = al.list(limit=limit)
    if not entries:
        console.print("[yellow]No audit entries[/yellow]")
        return
    table = Table(title="Audit Log")
    table.add_column("Time")
    table.add_column("Action")
    table.add_column("Actor")
    table.add_column("Resource")
    table.add_column("Hash")
    for e in entries:
        table.add_row(
            e.get("timestamp", "")[:19],
            e.get("action", ""),
            e.get("actor", ""),
            e.get("resource", "")[:40],
            e.get("hash", "")[:8],
        )
    console.print(table)
    if verify:
        ok = al.verify_chain()
        console.print(f"[dim]Chain verified: {'intact' if ok else '[red]BROKEN[/red]'}[/dim]")


@app.command()
def providers():
    """List configured LLM providers (secrets redacted)."""
    settings = _settings_or_exit()
    table = Table(title="LLM Providers")
    table.add_column("Name")
    table.add_column("Base URL")
    table.add_column("Model")
    table.add_column("Embedding")
    table.add_column("Has Key")
    table.add_column("Default")
    for name, p in settings.adapters.providers.items():
        has_key = bool(p.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("PKH_CUSTOM_API_KEY"))
        table.add_row(
            name,
            p.base_url or "-",
            p.model or "-",
            p.embedding_model or "-",
            "yes" if has_key else "no",
            "yes" if name == settings.adapters.default else "",
        )
    if settings.adapters.custom_base_url or settings.adapters.custom_model:
        has_key = bool(
            settings.adapters.custom_api_key
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("PKH_CUSTOM_API_KEY")
        )
        table.add_row(
            "custom",
            settings.adapters.custom_base_url or "-",
            settings.adapters.custom_model or "-",
            settings.adapters.custom_embedding_model or "-",
            "yes" if has_key else "no",
            "yes" if settings.adapters.default == "custom" else "",
        )
    for builtin in ("mock", "claude", "gpt", "gemini", "local"):
        table.add_row(
            builtin, "-", "-", "-", "-", "yes" if settings.adapters.default == builtin else ""
        )
    console.print(table)
    console.print(f"[dim]Default: {settings.adapters.default}[/dim]")


@app.command("export")
def export(
    export_format: str = typer.Option(
        "json", "--format", "-f", help=f"Output format: {' | '.join(EXPORT_FORMATS)}"
    ),
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Write to file (default: stdout)")
    ] = None,
    lifecycle: str | None = typer.Option(
        None, "--lifecycle", help="Filter by lifecycle state (e.g. ACTIVE)"
    ),
    entity_type: str | None = typer.Option(None, "--entity-type", help="Filter by entity type"),
    object_type: str | None = typer.Option(
        None, "--object-type", help="Filter by object type (ENTITY | RELATIONSHIP)"
    ),
    query: str | None = typer.Option(None, "--query", help="Text filter on title/content"),
    limit: int = typer.Option(1000, help="Max objects to export"),
):
    """Export knowledge objects to json, csv or markdown (stdout or --out FILE)."""
    if lifecycle:
        try:
            LifecycleState(lifecycle.upper())
        except ValueError as e:
            valid = ", ".join(s.value for s in LifecycleState)
            raise typer.BadParameter(f"unknown lifecycle {lifecycle!r} (valid: {valid})") from e
    if entity_type:
        try:
            EntityType(entity_type.upper())
        except ValueError as e:
            raise typer.BadParameter(
                f"unknown entity type {entity_type!r} "
                f"(valid: {', '.join(s.value for s in EntityType)})"
            ) from e
    if object_type:
        try:
            ObjectType(object_type.upper())
        except ValueError as e:
            raise typer.BadParameter(f"unknown object type {object_type!r}") from e
    # fail fast on the format before opening stores / touching the DB
    fmt = (export_format or "json").strip().lower()
    if fmt not in EXPORT_FORMATS:
        err_console.print(
            f"[red]Unknown format:[/red] {export_format!r} (supported: {', '.join(EXPORT_FORMATS)})"
        )
        raise typer.Exit(code=2)

    _settings_or_exit()
    store = get_store()
    filters: dict[str, object] = {}
    if entity_type:
        filters["entity_type"] = entity_type.upper()
    if object_type:
        filters["object_type"] = object_type.upper()
    if query:
        filters["query"] = query
    kos = store.metadata.query(
        filters=filters,
        lifecycle_states=[lifecycle.upper()] if lifecycle else None,
        limit=max(1, limit),
    )
    if not kos:
        console.print("[yellow]No knowledge objects matched the given filters[/yellow]")
        return
    if out is not None:
        out = out.expanduser()
        try:
            with open(out, "w", encoding="utf-8") as f:
                render_export(kos, fmt, f)
        except OSError as e:
            err_console.print(f"[red]Cannot write {out}: {e}[/red]")
            raise typer.Exit(code=1) from e
        console.print(f"[green]✓ Exported {len(kos)} objects to {out} ({fmt})[/green]")
    else:
        render_export(kos, fmt, sys.stdout)
    audit = AuditLog()
    audit.log(
        "export",
        details={"format": fmt, "count": len(kos), "out": str(out) if out else "stdout"},
    )


@app.command()
def doctor(
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON report"),
):
    """Health-check the environment: config, storage, git, audit chain, providers."""
    report = run_doctor()
    if json_out:
        console.print_json(
            json.dumps(
                {
                    "checks": [
                        {
                            "name": c.name,
                            "status": c.status,
                            "detail": c.detail,
                            "fix": c.fix,
                        }
                        for c in report.checks
                    ],
                    "failed": report.failed,
                    "warned": report.warned,
                },
                indent=2,
            )
        )
    else:
        table = Table(title="PKH Doctor")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        for c in report.checks:
            color = {"PASS": "green", "WARN": "yellow", "FAIL": "red"}.get(c.status, "white")
            table.add_row(c.name, f"[{color}]{c.status}[/{color}]", c.detail)
        console.print(table)
        fixes = [c for c in report.checks if c.status in ("FAIL", "WARN") and c.fix]
        for c in fixes:
            console.print(f"[dim]hint ({c.name}): {c.fix}[/dim]")
        summary_color = "red" if report.failed else ("yellow" if report.warned else "green")
        console.print(
            f"[bold {summary_color}]Doctor: {report.failed} failed, "
            f"{report.warned} warned, {len(report.checks) - report.failed - report.warned} passed"
            "[/]"
        )
    if report.failed:
        raise typer.Exit(code=1)


@app.command()
def sync(
    incremental: bool = typer.Option(False, help="Incremental sync (change detection)"),
):
    """Sync all sources — full ingest by default, incremental with --incremental."""
    if incremental:
        _settings_or_exit()

        async def _incr():
            from pkh.engines.ingestion.document_connector import DocumentConnector
            from pkh.engines.ingestion.git_connector import GitConnector
            from pkh.engines.ingestion.sync_manager import SyncManager

            mgr = SyncManager([GitConnector(repo_url="./"), DocumentConnector(paths=["./docs"])])
            since = datetime.now(timezone.utc) - timedelta(days=1)
            with console.status("[cyan]Detecting changes...[/cyan]"):
                res = await mgr.run_incremental_sync(since)
            console.print(f"[green]✓ Incremental sync: {res.total_items_processed} items[/green]")
            if res.errors:
                for err in res.errors:
                    console.print(f"  [yellow]⚠ {err}[/yellow]")
            audit = AuditLog()
            audit.log("sync", details={"incremental": True, "items": res.total_items_processed})

        asyncio.run(_incr())
    else:
        settings = _settings_or_exit()
        src_list = _resolve_sources(settings, None, None)
        asyncio.run(_run_ingest(src_list, settings))


if __name__ == "__main__":
    app()
