"""Confluence connector stub - fetches pages via REST API if configured."""

from __future__ import annotations

from datetime import datetime, timezone

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class ConfluenceConnector:
    source_type = SourceType.CONFLUENCE

    def __init__(
        self, base_url: str = "", spaces: list[str] | None = None, token: str | None = None
    ):
        self.base_url = base_url
        self.spaces = spaces or []
        self.token = token

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        if not self.base_url or not self.token:
            logger.info("Confluence not configured, returning 0 items")
            return []
        # Placeholder for real API call - use mock data for now
        import httpx

        items: list[RawItem] = []
        for space in self.spaces:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self.base_url}/rest/api/content",
                        params={"spaceKey": space, "limit": 50},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for page in data.get("results", []):
                            items.append(
                                RawItem(
                                    item_id=str(page.get("id")),
                                    source_type=SourceType.CONFLUENCE.value,
                                    title=page.get("title", ""),
                                    content=page.get("body", {})
                                    .get("storage", {})
                                    .get("value", ""),
                                    content_type="html",
                                    metadata={
                                        "space": space,
                                        "version": page.get("version", {}).get("number"),
                                    },
                                    updated_at=datetime.now(timezone.utc),
                                )
                            )
            except Exception as e:
                logger.warning(f"Confluence fetch failed for {space}: {e}")
        return items

    async def get_item(self, item_id: str) -> RawItem:
        raise NotImplementedError

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        return await self.list_items()

    def health_check(self) -> bool:
        return bool(self.base_url)
