import pytest

import mcp_server_dash
from dash_api import (
    DashSearchResponse,
    DashSearchResultItem,
    FileMetadata,
    GetLinkMetadataResponse,
    QueryResult,
)


class FakeTokenStore:
    def __init__(self, authed: bool, token: str | None = None):
        self._authed = authed
        self.access_token = token

    @property
    def is_authenticated(self):
        return self._authed

    def clear(self):
        self._authed = False
        self.access_token = None


class FakeAPI:
    def __init__(self, *_args, **_kwargs):
        pass

    async def search(self, _req):
        return DashSearchResponse(results=[])

    async def get_link_metadata(self, _req):
        return GetLinkMetadataResponse(results=[])


@pytest.mark.asyncio
async def test_auth_required_message(monkeypatch):
    monkeypatch.setattr(mcp_server_dash, "token_store", FakeTokenStore(authed=False))
    out = await mcp_server_dash.dash_company_search("x")
    assert "Not authenticated" in out


@pytest.mark.asyncio
async def test_search_no_results(monkeypatch):
    monkeypatch.setattr(mcp_server_dash, "token_store", FakeTokenStore(authed=True, token="t"))
    monkeypatch.setattr(mcp_server_dash, "DashAPI", FakeAPI)
    out = await mcp_server_dash.dash_company_search("nothing")
    assert "Found 0 results" in out


@pytest.mark.asyncio
async def test_search_happy_path(monkeypatch):
    class FakeAPIWithResult(FakeAPI):
        async def search(self, _req):
            item = DashSearchResultItem(
                query_result=QueryResult(uuid="u1", title="Title", url="https://x")
            )
            return DashSearchResponse(results=[item])

    monkeypatch.setattr(mcp_server_dash, "token_store", FakeTokenStore(authed=True, token="t"))
    monkeypatch.setattr(mcp_server_dash, "DashAPI", FakeAPIWithResult)
    out = await mcp_server_dash.dash_company_search("q")
    assert "Found 1 results" in out
    assert "Title" in out


@pytest.mark.asyncio
async def test_file_details_truncation(monkeypatch):
    big = "x" * 25000
    meta = FileMetadata(title="T", body={"blob_content": {"raw": big, "mime_type": "text/plain"}})
    resp = GetLinkMetadataResponse(results=[meta])

    class FakeAPIFile(FakeAPI):
        async def get_link_metadata(self, _req):
            return resp

    monkeypatch.setattr(mcp_server_dash, "token_store", FakeTokenStore(authed=True, token="t"))
    monkeypatch.setattr(mcp_server_dash, "DashAPI", FakeAPIFile)
    out = await mcp_server_dash.dash_get_file_details("uuid")
    assert "Content truncated" in out
