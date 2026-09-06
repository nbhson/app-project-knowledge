"""Jira connector with cursor pagination, JQL escaping, and single AsyncClient reuse."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


def _escape_jql_value(value: str) -> str:
    """Escape a JQL string value for safe inclusion in quoted context.

    JQL uses double-quoted strings; escape backslashes and quotes.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


class JiraConnector:
    source_type = SourceType.JIRA

    def __init__(
        self,
        base_url: str = "",
        projects: list[str] | None = None,
        token: str | None = None,
        email: str | None = None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.projects = projects or []
        self.token = token
        self.email = email
        self._client: Any | None = None

    # ------------------------------------------------------------------ auth
    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header.

        NOTE: Atlassian Cloud Jira expects HTTP Basic with
        ``email:api_token`` base64-encoded (same as Confluence).
        Bearer is for OAuth 2.0.  We emit Basic when email is supplied,
        otherwise Bearer as fallback for OAuth/PAT.
        """
        if not self.token:
            return {}
        if self.email:
            cred = f"{self.email}:{self.token}"
            b64 = base64.b64encode(cred.encode()).decode()
            return {"Authorization": f"Basic {b64}"}
        return {"Authorization": f"Bearer {self.token}"}

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=10)
        return self._client

    async def connect(self) -> None:
        self._get_client()

    async def disconnect(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _issue_to_raw(issue: dict[str, Any], proj: str) -> RawItem:
        fields = issue.get("fields", {})
        return RawItem(
            item_id=issue.get("key") or str(issue.get("id", "")),
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

    # ------------------------------------------------------------------ public
    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        if not self.base_url or not self.token:
            logger.info("Jira not configured, returning 0 items")
            return []

        client = self._get_client()
        headers = self._auth_headers()
        items: list[RawItem] = []

        for proj in self.projects:
            escaped = _escape_jql_value(proj)
            jql = f'project="{escaped}"'

            # cursor can be startAt (numeric) or nextPageToken (opaque)
            start_at = 0
            next_page_token: str | None = None
            if cursor is not None:
                if cursor.isdigit():
                    start_at = int(cursor)
                else:
                    next_page_token = cursor

            while True:
                params: dict[str, Any] = {"jql": jql, "maxResults": 50}
                if next_page_token is not None:
                    params["nextPageToken"] = next_page_token
                else:
                    params["startAt"] = start_at

                try:
                    resp = await client.get(
                        f"{self.base_url}/rest/api/3/search",
                        params=params,
                        headers=headers,
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Jira fetch failed for {proj}: {resp.status_code}")
                        break
                    data = resp.json()
                    issues = data.get("issues", [])
                    for issue in issues:
                        items.append(self._issue_to_raw(issue, proj))

                    # pagination: prefer nextPageToken (Jira Cloud) else startAt/total
                    token = data.get("nextPageToken") or data.get("next_page_token")
                    if token:
                        next_page_token = str(token)
                        if not next_page_token:
                            break
                        continue
                    # fallback startAt pagination
                    total = data.get("total")
                    if total is not None:
                        if start_at + len(issues) >= total:
                            break
                        if len(issues) < 50:
                            break
                        start_at += len(issues)
                        next_page_token = None
                        continue
                    # if total missing, rely on size < limit
                    if len(issues) < 50:
                        break
                    start_at += 50
                    next_page_token = None
                except Exception as e:
                    logger.warning(f"Jira fetch failed for {proj}: {e}")
                    break
        return items

    async def get_item(self, item_id: str) -> RawItem:
        """Fetch a single Jira issue by key/id."""
        if not self.base_url or not self.token:
            raise ValueError("Jira not configured (base_url/token required)")
        client = self._get_client()
        headers = self._auth_headers()
        # issue keys may contain special chars; URL-encode via httpx param handling
        resp = await client.get(
            f"{self.base_url}/rest/api/3/issue/{item_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 404:
            raise FileNotFoundError(f"Jira issue not found: {item_id}")
        if resp.status_code != 200:
            raise RuntimeError(f"Jira get_item failed {resp.status_code}: {resp.text[:200]}")
        issue = resp.json()
        # derive project from issue key prefix (e.g. PROJ-123)
        proj = ""
        key = issue.get("key", item_id)
        if "-" in key:
            proj = key.split("-", 1)[0]
        return self._issue_to_raw(issue, proj)

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        return await self.list_items()

    def health_check(self) -> bool:
        return bool(self.base_url)
