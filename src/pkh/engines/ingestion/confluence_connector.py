"""Confluence connector - fetches pages via REST API with cursor pagination."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from pkh.engines.ingestion.models import RawItem
from pkh.models.knowledge import SourceType
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class ConfluenceConnector:
    source_type = SourceType.CONFLUENCE

    def __init__(
        self,
        base_url: str = "",
        spaces: list[str] | None = None,
        token: str | None = None,
        email: str | None = None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.spaces = spaces or []
        self.token = token
        self.email = email
        self._client: Any | None = None  # httpx.AsyncClient, lazy to avoid import at init

    # ------------------------------------------------------------------ auth
    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header.

        NOTE: Atlassian Cloud Confluence expects HTTP Basic with
        ``email:api_token`` base64-encoded.  ``Bearer <token>`` is for
        OAuth 2.0 flows and will 401 when an API token is supplied.
        We support both: if *email* is provided we emit Basic, otherwise
        fall back to Bearer for OAuth / PAT setups.
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
        # reuse single client per connector lifetime
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
    def _page_to_raw(page: dict[str, Any], space: str) -> RawItem:
        return RawItem(
            item_id=str(page.get("id")),
            source_type=SourceType.CONFLUENCE.value,
            title=page.get("title", ""),
            content=page.get("body", {}).get("storage", {}).get("value", ""),
            content_type="html",
            metadata={
                "space": space,
                "version": page.get("version", {}).get("number"),
            },
            updated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------ public
    async def list_items(self, cursor: str | None = None) -> list[RawItem]:
        if not self.base_url or not self.token:
            logger.info("Confluence not configured, returning 0 items")
            return []

        client = self._get_client()
        headers = self._auth_headers()
        items: list[RawItem] = []

        # cursor may be an opaque token (nextPageToken) or numeric start offset
        # For multi-space case we treat cursor as per-connector start offset;
        # when nextPageToken is returned we loop with that token.
        for space in self.spaces:
            start = 0
            next_page_token: str | None = cursor
            # if cursor looks numeric, treat as start offset
            if cursor and cursor.isdigit():
                start = int(cursor)
                next_page_token = None

            while True:
                params: dict[str, Any] = {
                    "spaceKey": space,
                    "limit": 50,
                    "expand": "body.storage,version",
                }
                if next_page_token and not next_page_token.isdigit():
                    # Confluence Cloud v2 uses cursor/nextPageToken
                    params["cursor"] = next_page_token
                    # also try nextPageToken param for compatibility
                    params["nextPageToken"] = next_page_token
                else:
                    params["start"] = start

                try:
                    resp = await client.get(
                        f"{self.base_url}/rest/api/content",
                        params=params,
                        headers=headers,
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Confluence fetch failed for {space}: {resp.status_code}")
                        break
                    data = resp.json()
                    results = data.get("results", [])
                    for page in results:
                        items.append(self._page_to_raw(page, space))

                    # pagination: prefer nextPageToken (Cloud v2) else start/limit
                    token = data.get("nextPageToken") or data.get("next_page_token")
                    if token:
                        next_page_token = str(token)
                        # empty token means end
                        if not next_page_token:
                            break
                        # continue loop with new token; do not increment start
                        continue
                    # fallback: check _links.next existence or size < limit
                    links_next = data.get("_links", {}).get("next")
                    if links_next:
                        start += 50
                        next_page_token = None
                        continue
                    if len(results) < 50:
                        break
                    start += 50
                    next_page_token = None
                except Exception as e:
                    logger.warning(f"Confluence fetch failed for {space}: {e}")
                    break
        return items

    async def get_item(self, item_id: str) -> RawItem:
        """Fetch a single Confluence page by id."""
        if not self.base_url or not self.token:
            raise ValueError("Confluence not configured (base_url/token required)")
        client = self._get_client()
        headers = self._auth_headers()
        resp = await client.get(
            f"{self.base_url}/rest/api/content/{item_id}",
            params={"expand": "body.storage,version"},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 404:
            raise FileNotFoundError(f"Confluence page not found: {item_id}")
        if resp.status_code != 200:
            raise RuntimeError(f"Confluence get_item failed {resp.status_code}: {resp.text[:200]}")
        page = resp.json()
        # space is inside page['space']['key'] if available, else unknown
        space = ""
        try:
            space = page.get("space", {}).get("key", "") or page.get("spaceKey", "")
        except Exception:
            space = ""
        return self._page_to_raw(page, space)

    async def detect_changes(self, since: datetime) -> list[RawItem]:
        return await self.list_items()

    def health_check(self) -> bool:
        return bool(self.base_url)
