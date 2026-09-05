"""Jira connector stub."""

from __future__ import annotations

from datetime import datetime, timezone

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class JiraConnector:
    source_type = SourceType.JIRA

    def __init__(
        self, base_url: str = "", projects: list[str] | None = None, token: str | None = None
    ):
        self.base_url = base_url
        self.projects = projects or []
        self.token = token

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        if not self.base_url or not self.token:
            logger.info("Jira not configured, returning 0 items")
            return []
        import httpx

        items: list[RawItem] = []
        for proj in self.projects:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self.base_url}/rest/api/3/search",
                        params={"jql": f"project={proj}", "maxResults": 50},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for issue in data.get("issues", []):
                            fields = issue.get("fields", {})
                            items.append(
                                RawItem(
                                    item_id=issue.get("key"),
                                    source_type=SourceType.JIRA.value,
                                    title=fields.get("summary", ""),
                                    content=fields.get("description", "") or "",
                                    content_type="text",
                                    metadata={
                                        "issue_type": fields.get("issuetype", {}).get("name"),
                                        "status": fields.get("status", {}).get("name"),
                                        "project": proj,
                                    },
                                    updated_at=datetime.now(timezone.utc),
                                )
                            )
            except Exception as e:
                logger.warning(f"Jira fetch failed for {proj}: {e}")
        return items

    async def get_item(self, item_id: str) -> RawItem:
        raise NotImplementedError

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        return await self.list_items()

    def health_check(self) -> bool:
        return bool(self.base_url)
