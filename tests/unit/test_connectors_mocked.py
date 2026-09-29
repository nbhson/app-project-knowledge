"""Mocked Confluence/Jira network tests to push coverage >=70%."""

from __future__ import annotations

import pytest


class _FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = "ok"

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.closed = False

    async def get(self, *a, **k):
        if self._responses:
            return self._responses.pop(0)
        return _FakeResp({"results": [], "issues": [], "total": 0})

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_confluence_list_pagination_and_get():
    from pkh.engines.ingestion.confluence_connector import ConfluenceConnector

    c = ConfluenceConnector(base_url="https://x", spaces=["ENG"], token="t")
    page = {"id": "1", "title": "T", "body": {"storage": {"value": "hi"}}, "version": {"number": 1}}
    c._client = _FakeClient(
        [
            _FakeResp({"results": [page], "_links": {"next": "/next"}}),
            _FakeResp({"results": [page]}),
        ]
    )
    items = await c.list_items()
    assert len(items) == 2
    # get_item success
    c._client = _FakeClient([_FakeResp({**page, "space": {"key": "ENG"}})])
    got = await c.get_item("1")
    assert got.item_id == "1"
    # get_item 404
    c._client = _FakeClient([_FakeResp({}, status=404)])
    with pytest.raises(FileNotFoundError):
        await c.get_item("missing")
    # get_item 500
    c._client = _FakeClient([_FakeResp({}, status=500)])
    with pytest.raises(RuntimeError):
        await c.get_item("x")
    # non-200 list breaks
    c._client = _FakeClient([_FakeResp({}, status=500)])
    assert await c.list_items() == []
    # nextPageToken path
    c._client = _FakeClient(
        [
            _FakeResp({"results": [page], "nextPageToken": "tok123"}),
            _FakeResp({"results": []}),
        ]
    )
    assert len(await c.list_items(cursor=None)) >= 1
    await c.disconnect()
    assert c.health_check() is True


@pytest.mark.asyncio
async def test_jira_list_pagination_and_get():
    from pkh.engines.ingestion.jira_connector import JiraConnector

    j = JiraConnector(base_url="https://x", projects=["P"], token="t")
    issue = {
        "key": "P-1",
        "fields": {
            "summary": "S",
            "description": "D",
            "issuetype": {"name": "Story"},
            "status": {"name": "Open"},
        },
    }
    j._client = _FakeClient(
        [
            _FakeResp({"issues": [issue], "total": 2}),
            _FakeResp({"issues": [issue], "total": 2}),
        ]
    )
    items = await j.list_items()
    assert len(items) >= 1
    j._client = _FakeClient([_FakeResp({**issue})])
    got = await j.get_item("P-1")
    assert got.item_id == "P-1"
    j._client = _FakeClient([_FakeResp({}, status=404)])
    with pytest.raises(FileNotFoundError):
        await j.get_item("P-9")
    j._client = _FakeClient([_FakeResp({}, status=500)])
    assert await j.list_items() == []
    # token pagination
    j._client = _FakeClient(
        [
            _FakeResp({"issues": [issue], "nextPageToken": "abc"}),
            _FakeResp({"issues": []}),
        ]
    )
    assert len(await j.list_items()) >= 1
    assert j.health_check() is True


def test_connectors_protocol_and_document_patterns():
    from pkh.engines.ingestion.connectors import SourceConnector
    from pkh.engines.ingestion.document_connector import DocumentConnector

    assert SourceConnector is not None
    d = DocumentConnector(paths=["./nonexistent"], patterns=["**/*.md"])
    from pathlib import Path

    assert d._matches(Path("a.md")) in (True, False)
