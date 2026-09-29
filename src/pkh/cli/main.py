"""CLI with Typer + Rich."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pkh.adapters import get_adapter
from pkh.config.settings import get_settings
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.confluence_connector import ConfluenceConnector
from pkh.engines.ingestion.document_connector import DocumentConnector
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.jira_connector import JiraConnector
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.governance.audit import AuditLog
from pkh.models.knowledge import LifecycleState
from pkh.services.query import run_query_pipeline
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

app = typer.Typer(help="Project Knowledge Harness CLI")
console = Console()

# CLI singleton per process (fix-plan 1.6)
_store_cli: KnowledgeStore | None = None
_store_cli_key: tuple[str, str, str] | None = None


def _store_key_from_settings() -> tuple[str, str, str]:
    s = get_settings()
    return (
        s.storage.metadata.sqlite_path,
        s.storage.vector.path,
        s.storage.graph.persist_path,
    )


def _create_store() -> KnowledgeStore:
    s = get_settings()
    return KnowledgeStore(
        metadata_path=s.storage.metadata.sqlite_path,
        vector_path=s.storage.vector.path,
        graph_path=s.storage.graph.persist_path,
    )


def get_store() -> KnowledgeStore:
    global _store_cli, _store_cli_key
    key = _store_key_from_settings()
    if _store_cli is None or _store_cli_key != key:
        _store_cli = _create_store()
        _store_cli_key = key
    return _store_cli


@app.command()
def init(
    path: str = typer.Option(".", help="Path to init"),
    force: bool = typer.Option(False, help="Overwrite existing"),
):
    """Scaffold config."""
    setup_logging()
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
        console.print(f"[green]Created {dest} from example[/green]")
    else:
        dest.write_text("# PKH settings\nstorage:\n  metadata:\n    sqlite_path: ./data/pkh.db\n")
        console.print(f"[green]Created {dest}[/green]")
    console.print(f"[dim]Edit {dest} to configure sources[/dim]")


@app.command()
def ingest(
    source: str | None = typer.Option(
        None, "--source", help="Source URL like git://./path or confluence://SPACE"
    ),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated sources"),
    sync: bool = typer.Option(False, help="Incremental sync"),
):
    """Ingest from sources."""
    setup_logging()
    settings = get_settings()

    src_list: list[str] = []
    if sources:
        src_list.extend([s.strip() for s in sources.split(",") if s.strip()])
    if source:
        src_list.append(source)
    if not src_list:
        # try config sources
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

    async def _run():
        store = get_store()
        total_kos = 0
        for src in src_list:
            console.print(f"[cyan]Ingesting {src} ...[/cyan]")
            try:
                if src.startswith("git://"):
                    path = src[6:]
                    conn = GitConnector(repo_url=path)
                elif src.startswith("confluence://"):
                    space = src[len("confluence://") :]
                    conn = ConfluenceConnector(
                        base_url=settings.sources.confluence.url, spaces=[space]
                    )
                elif src.startswith("jira://"):
                    proj = src[len("jira://") :]
                    conn = JiraConnector(base_url=settings.sources.jira.url, projects=[proj])
                elif src.startswith("document://"):
                    p = src[len("document://") :]
                    conn = DocumentConnector(paths=[p])
                else:
                    conn = GitConnector(repo_url=src)

                mgr = SyncManager([conn])
                items = await mgr.collect_all()
                console.print(f"  [dim]Collected {len(items)} raw items[/dim]")
                if not items:
                    console.print("  [yellow]No items found, skipping[/yellow]")
                    continue
                pipeline = ExtractionPipeline(
                    llm_enabled=settings.extraction.llm_enabled,
                    llm_adapter=(
                        get_adapter(settings.extraction.llm_adapter)
                        if settings.extraction.llm_enabled
                        else None
                    ),
                    budget_tokens=settings.extraction.budget_per_run_tokens,
                    batch_size=settings.extraction.batch_size,
                )
                kos, stats = await pipeline.run(items)
                # Transition via state machine to ACTIVE for querying
                from pkh.models.lifecycle import transition as lifecycle_transition

                transitioned = []
                for ko in kos:
                    try:
                        if ko.lifecycle_state == LifecycleState.DISCOVERED:
                            ko = lifecycle_transition(
                                ko, LifecycleState.EXTRACTED, reason="cli-ingest"
                            )
                            ko = lifecycle_transition(
                                ko, LifecycleState.VALIDATING, reason="cli-ingest"
                            )
                            ko = lifecycle_transition(
                                ko, LifecycleState.ACTIVE, reason="cli-ingest"
                            )
                        elif ko.lifecycle_state == LifecycleState.EXTRACTED:
                            ko = lifecycle_transition(
                                ko, LifecycleState.VALIDATING, reason="cli-ingest"
                            )
                            ko = lifecycle_transition(
                                ko, LifecycleState.ACTIVE, reason="cli-ingest"
                            )
                        elif ko.lifecycle_state == LifecycleState.VALIDATING:
                            ko = lifecycle_transition(
                                ko, LifecycleState.ACTIVE, reason="cli-ingest"
                            )
                    except Exception as e:
                        logger.warning(f"Lifecycle transition failed for {ko.id}: {e}")
                    transitioned.append(ko)
                kos = transitioned
                await store.save(kos)
                total_kos += len(kos)
                console.print(f"  [green]Extracted {len(kos)} knowledge objects[/green] {stats}")
            except Exception as e:
                console.print(f"  [red]Failed {src}: {e}[/red]")
        console.print(f"[bold green]Ingest done: {total_kos} knowledge objects[/bold green]")
        audit = AuditLog()
        audit.log("ingest", resource=",".join(src_list), details={"count": total_kos})

    asyncio.run(_run())


def _resolve_cli_adapter(
    settings,
    provider: str | None,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
):
    """Resolve adapter with CLI overrides (explicit flags win over settings/env)."""
    import os as _os

    name = provider or settings.adapters.default
    key = api_key or _os.getenv("PKH_CUSTOM_API_KEY") or _os.getenv("OPENAI_API_KEY")
    return get_adapter(
        name,
        base_url=base_url,
        model=model,
        api_key=key,
    )


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
    """Natural language query."""
    setup_logging()
    settings = get_settings()

    async def _run():
        store = get_store()
        package, search_stats, intent = await run_query_pipeline(store, question, top_k=top_k)
        console.print(f"[dim]Intent: {intent.value}[/dim]")

        from pkh.utils.exceptions import AdapterError, ConfigurationError

        try:
            adapter = _resolve_cli_adapter(settings, provider, base_url, model, api_key)
            answer = await adapter.complete(package)
        except ConfigurationError as e:
            console.print(f"[red]Provider not configured: {e}[/red]")
            raise typer.Exit(code=2) from e
        except AdapterError as e:
            console.print(f"[red]Provider request failed: {e}[/red]")
            raise typer.Exit(code=2) from e

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

    asyncio.run(_run())


@app.command()
def context(
    query: str = typer.Option(..., "--query", help="Query to get context for"),
    top_k: int = typer.Option(5, help="Top K"),
    provider: str | None = typer.Option(
        None, "--provider", help="LLM provider for answer (default: context only)"
    ),
    model: str | None = typer.Option(None, "--model", help="Custom provider model override"),
):
    """Get raw ContextPackage JSON."""
    setup_logging()
    settings = get_settings()

    async def _run():
        store = get_store()
        package, _, intent = await run_query_pipeline(store, query, top_k=top_k)
        if provider or model:
            from pkh.utils.exceptions import AdapterError, ConfigurationError

            try:
                adapter = _resolve_cli_adapter(settings, provider, None, model, None)
                answer = await adapter.complete(package)
                console.print(f"[bold]Answer ({provider or settings.adapters.default}):[/bold]")
                console.print(answer)
            except (AdapterError, ConfigurationError) as e:
                console.print(f"[red]Provider failed: {e}[/red]")
                raise typer.Exit(code=2) from e
        console.print_json(
            json.dumps(package.model_dump(mode="json"), indent=2, ensure_ascii=False)
        )

    asyncio.run(_run())


@app.command()
def graph(
    entity: str = typer.Option(..., "--entity", help="Entity name or ID"),
    depth: int = typer.Option(2, help="Traversal depth"),
):
    """Visualize knowledge graph."""
    setup_logging()
    store = get_store()
    depth = max(1, min(int(depth), 5))

    # find entity by name — score all candidates, pick best title match
    kos = store.metadata.query(filters={"query": entity}, limit=5)
    if not kos:
        console.print(f"[red]Entity not found: {entity}[/red]")
        raise typer.Exit(code=1)
    # prefer exact title match, else first
    target = next((k for k in kos if k.title.lower() == entity.lower()), kos[0])
    console.print(f"[cyan]Entity: {target.title} ({target.id}) type={target.entity_type}[/cyan]")
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
    """Check status."""
    setup_logging()
    store = get_store()

    async def _run():
        hc = await store.health_check()
        table = Table(title="PKH Status")
        table.add_column("Component")
        table.add_column("Count")
        table.add_row("Metadata (SQLite)", str(hc.get("metadata_count", 0)))
        table.add_row("Vector", str(hc.get("vector_count", 0)))
        table.add_row("Graph Nodes", str(hc.get("graph_nodes", 0)))
        table.add_row("Graph Edges", str(hc.get("graph_edges", 0)))
        console.print(table)
        # audit
        audit = AuditLog()
        entries = audit.list(limit=5)
        console.print(f"[dim]Recent audit entries: {len(entries)}[/dim]")
        for e in entries:
            console.print(f"  {e.get('timestamp')} {e.get('action')} {e.get('resource')}")

    asyncio.run(_run())


@app.command()
def audit(
    limit: int = typer.Option(20, help="Limit"),
):
    """View audit log."""
    setup_logging()
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
    console.print(f"[dim]Chain verified: {al.verify_chain()}[/dim]")


@app.command()
def providers():
    """List configured LLM providers (secrets redacted)."""
    import os as _os

    setup_logging()
    settings = get_settings()
    table = Table(title="LLM Providers")
    table.add_column("Name")
    table.add_column("Base URL")
    table.add_column("Model")
    table.add_column("Embedding")
    table.add_column("Has Key")
    table.add_column("Default")
    for name, p in settings.adapters.providers.items():
        has_key = bool(
            p.api_key or _os.getenv("OPENAI_API_KEY") or _os.getenv("PKH_CUSTOM_API_KEY")
        )
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
            or _os.getenv("OPENAI_API_KEY")
            or _os.getenv("PKH_CUSTOM_API_KEY")
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


@app.command()
def sync(
    incremental: bool = typer.Option(False, help="Incremental sync"),
):
    """Sync all sources."""
    if incremental:
        import asyncio as asyncio_lib
        from datetime import datetime, timedelta, timezone

        from pkh.engines.ingestion.document_connector import DocumentConnector
        from pkh.engines.ingestion.git_connector import GitConnector
        from pkh.engines.ingestion.sync_manager import SyncManager

        async def _incr():
            mgr = SyncManager([GitConnector(repo_url="./"), DocumentConnector(paths=["./docs"])])
            since = datetime.now(timezone.utc) - timedelta(days=1)
            res = await mgr.run_incremental_sync(since)
            console.print(f"[green]Incremental sync: {res.total_items_processed} items[/green]")

        asyncio_lib.run(_incr())
    else:
        ingest(source=None, sources=None, sync=False)


if __name__ == "__main__":
    app()
