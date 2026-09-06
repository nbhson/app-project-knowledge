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
from pkh.engines.context_delivery.assembler import ContextAssembler
from pkh.engines.context_delivery.compressor import compress
from pkh.engines.context_delivery.models import SearchStats
from pkh.engines.context_delivery.validator import ContextValidator
from pkh.engines.extraction.pipeline import ExtractionPipeline
from pkh.engines.ingestion.confluence_connector import ConfluenceConnector
from pkh.engines.ingestion.document_connector import DocumentConnector
from pkh.engines.ingestion.git_connector import GitConnector
from pkh.engines.ingestion.jira_connector import JiraConnector
from pkh.engines.ingestion.sync_manager import SyncManager
from pkh.engines.retrieval.intent import QueryPlanner, classify_intent
from pkh.engines.retrieval.reranker import deduplicate, rerank
from pkh.engines.retrieval.retriever import HybridRetriever
from pkh.governance.audit import AuditLog
from pkh.models.knowledge import LifecycleState
from pkh.storage.unified import KnowledgeStore
from pkh.utils.logging import setup_logging

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
    example = Path("config/settings.yaml.example")
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
                pipeline = ExtractionPipeline(llm_enabled=settings.extraction.llm_enabled)
                kos, stats = await pipeline.run(items)
                # Transition via state machine to ACTIVE for querying
                from pkh.models.lifecycle import transition as lifecycle_transition

                for ko in kos:
                    if ko.lifecycle_state == LifecycleState.DISCOVERED:
                        ko = lifecycle_transition(ko, LifecycleState.EXTRACTED)
                        ko = lifecycle_transition(ko, LifecycleState.VALIDATING)
                        ko = lifecycle_transition(ko, LifecycleState.ACTIVE)
                    elif ko.lifecycle_state == LifecycleState.EXTRACTED:
                        ko = lifecycle_transition(ko, LifecycleState.VALIDATING)
                        ko = lifecycle_transition(ko, LifecycleState.ACTIVE)
                    elif ko.lifecycle_state == LifecycleState.VALIDATING:
                        ko = lifecycle_transition(ko, LifecycleState.ACTIVE)
                await store.save(kos)
                total_kos += len(kos)
                console.print(f"  [green]Extracted {len(kos)} knowledge objects[/green] {stats}")
            except Exception as e:
                console.print(f"  [red]Failed {src}: {e}[/red]")
        console.print(f"[bold green]Ingest done: {total_kos} knowledge objects[/bold green]")
        audit = AuditLog()
        audit.log("ingest", resource=",".join(src_list), details={"count": total_kos})

    asyncio.run(_run())


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural language query"),
    top_k: int = typer.Option(5, help="Top K results"),
    show_context: bool = typer.Option(False, help="Show raw context package"),
):
    """Natural language query."""
    setup_logging()
    settings = get_settings()

    async def _run():
        store = get_store()
        intent = classify_intent(question)
        console.print(f"[dim]Intent: {intent.value}[/dim]")
        retriever = HybridRetriever(store)
        planner = QueryPlanner()
        sub_qs = planner.plan(question, intent)
        all_fused = []
        stats_total: dict = {}
        import time

        start = time.time()
        for sq in sub_qs:
            fused, stats = await retriever.retrieve(sq, top_k=top_k)
            all_fused.extend(fused)
            for k, v in stats.items():
                stats_total[k] = stats_total.get(k, 0) + v

        all_fused = deduplicate(all_fused)
        all_fused = rerank(all_fused)
        active = [
            p for p in all_fused if p[0].lifecycle_state.value in ("ACTIVE", "UPDATED", "EXTRACTED")
        ]
        if not active:
            active = all_fused

        assembler = ContextAssembler(store)
        search_stats = SearchStats(
            vector_results=stats_total.get("vector", 0),
            keyword_results=stats_total.get("keyword", 0),
            graph_results=stats_total.get("graph", 0),
            total_before_dedup=len(all_fused),
            total_after_dedup=len(active),
            strategies_used=list(stats_total.keys()),
            latency_ms=(time.time() - start) * 1000,
        )
        package = await assembler.assemble(
            question, active[:top_k], intent=intent, search_stats=search_stats
        )
        package = compress(package)
        validator = ContextValidator()
        vr = validator.validate(package)
        if vr.warnings:
            for w in vr.warnings:
                if w not in package.warnings:
                    package.warnings.append(w)

        adapter = get_adapter(settings.adapters.default)
        answer = await adapter.complete(package)

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
):
    """Get raw ContextPackage JSON."""
    setup_logging()

    async def _run():
        store = get_store()
        intent = classify_intent(query)
        retriever = HybridRetriever(store)
        fused, stats = await retriever.retrieve(query, top_k=top_k)
        fused = deduplicate(fused)
        fused = rerank(fused)
        assembler = ContextAssembler(store)
        search_stats = SearchStats(
            vector_results=stats.get("vector", 0),
            keyword_results=stats.get("keyword", 0),
            graph_results=stats.get("graph", 0),
            total_before_dedup=len(fused),
            total_after_dedup=len(fused),
            strategies_used=list(stats.keys()),
        )
        package = await assembler.assemble(
            query, fused[:top_k], intent=intent, search_stats=search_stats
        )
        package = compress(package)
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

    # find entity by name
    kos = store.metadata.query(filters={"query": entity}, limit=5)
    if not kos:
        console.print(f"[red]Entity not found: {entity}[/red]")
        raise typer.Exit(code=1)
    target = kos[0]
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
def sync(
    incremental: bool = typer.Option(False, help="Incremental sync"),
):
    """Sync all sources."""
    ingest(source=None, sources=None, sync=incremental)


if __name__ == "__main__":
    app()
