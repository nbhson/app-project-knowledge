"""Mock adapter for testing."""

from __future__ import annotations

from pkh.engines.context_delivery.models import ContextPackage


class MockAdapter:
    def format_context(self, context: ContextPackage) -> str:
        lines = [
            f"Query: {context.query}",
            f"Intent: {context.intent}",
            f"Confidence: {context.confidence:.2f}",
            "",
        ]
        lines.append("## Knowledge")
        for c in context.knowledge:
            lines.append(f"- [{c.type}] {c.title} (conf={c.confidence:.2f}, rank={c.rank})")
            lines.append(f"  {c.content[:300]}")
            if c.sources:
                lines.append(f"  Sources: {', '.join(s.url or s.source_id for s in c.sources[:1])}")
        lines.append("")
        lines.append("## Relationships")
        for r in context.relationships:
            lines.append(f"- {r.from_id} --{r.type}--> {r.to_id} (conf={r.confidence:.2f})")
        lines.append("")
        lines.append("## Sources")
        for s in context.sources:
            lines.append(f"- {s.source_type.value}: {s.source_id} {s.url or ''}")
        return "\n".join(lines)

    # adapt alias per core/7-context-contract — keep both for compatibility
    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str:
        return self.format_context(context)

    async def complete(self, context: ContextPackage, model_config: dict | None = None) -> str:
        # mock answer based on knowledge (no LLM call when llm_enabled=false per adr-004)
        if not context.knowledge:
            return "I don't have relevant knowledge to answer this query."
        top = context.knowledge[0]
        sources = ", ".join(s.source_id for s in top.sources)
        return (
            f"Based on {top.title} (confidence {top.confidence:.2f}): "
            f"{top.content[:500]}\n\nSources: {sources}"
        )

    def parse_response(self, response: str) -> dict:
        return {"answer": response}

    def get_token_limit(self, model_config: dict | None = None) -> int:
        return 8000

    async def enrich(self, content: str) -> list:
        # No enrichment in mock
        return []
