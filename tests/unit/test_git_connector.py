import pytest

from pkh.engines.ingestion.git_connector import GitConnector


@pytest.mark.asyncio
async def test_git_connector_list_files(sample_git_repo):
    conn = GitConnector(repo_url=str(sample_git_repo))
    await conn.connect()
    items = await conn.list_items()
    assert len(items) >= 2
    ids = [i.item_id for i in items]
    assert any("payment.py" in x for x in ids)


@pytest.mark.asyncio
async def test_git_connector_health(sample_git_repo):
    conn = GitConnector(repo_url=str(sample_git_repo))
    assert conn.health_check()
    await conn.connect()
    assert conn.health_check()


@pytest.mark.asyncio
async def test_git_detect_changes(sample_git_repo):
    import datetime

    conn = GitConnector(repo_url=str(sample_git_repo))
    await conn.connect()
    since = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    changes = await conn.detect_changes(since)
    assert isinstance(changes, list)
