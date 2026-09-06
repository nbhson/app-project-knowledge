"""ModelAdapter protocol."""

from __future__ import annotations

from typing import Protocol

from pkh.engines.context_delivery.models import ContextPackage


class ModelAdapter(Protocol):
    async def complete(self, context: ContextPackage, model_config: dict) -> str: ...
    def format_context(self, context: ContextPackage) -> str: ...

    # adapt is alias to format_context for backwards compat per core/7-context-contract
    def adapt(self, context: ContextPackage, model_config: dict | None = None) -> str: ...

    def parse_response(self, response: str) -> dict: ...
    def get_token_limit(self, model_config: dict) -> int: ...
