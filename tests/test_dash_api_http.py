import httpx
import pytest
import respx

from dash_api import DashAPI, DashSearchRequest, GetLinkMetadataRequest


@pytest.mark.asyncio
async def test_search_success_http():
    api = DashAPI("token")
    url = "https://api.dropboxapi.com/2/dcs/search_mcp"
    payload = {
        "results": [
            {
                "query_result": {
                    "uuid": "u1",
                    "title": "Doc",
                    "url": "https://x",
                }
            }
        ]
    }
    with respx.mock(assert_all_called=True) as router:
        router.post(url).mock(return_value=httpx.Response(200, json=payload))
        resp = await api.search(DashSearchRequest(query_text="q"))
        assert len(resp.results) == 1


@pytest.mark.asyncio
async def test_unauthorized_raises_permission_error():
    api = DashAPI("token")
    url = "https://api.dropboxapi.com/2/dcs/search_mcp"
    with respx.mock(assert_all_called=True) as router:
        router.post(url).mock(return_value=httpx.Response(401, json={}))
        with pytest.raises(PermissionError):
            await api.search(DashSearchRequest(query_text="q"))


@pytest.mark.asyncio
async def test_retry_on_429_then_success(monkeypatch):
    api = DashAPI("token")
    url = "https://api.dropboxapi.com/2/dcs/search_mcp"

    # Speed up backoff during test
    api._backoff_base = 0.01
    payload = {"results": []}
    with respx.mock(assert_all_called=True) as router:
        calls = router.post(url)
        calls.side_effect = [
            httpx.Response(429, headers={"retry-after": "0.01"}),
            httpx.Response(200, json=payload),
        ]
        resp = await api.search(DashSearchRequest(query_text="q"))
        assert len(resp.results) == 0


@pytest.mark.asyncio
async def test_get_link_metadata_success():
    api = DashAPI("token")
    url = "https://api.dropboxapi.com/2/dcs/get_link_metadata_mcp"
    payload = {
        "results": [
            {"title": "T", "mime_type": "text/plain", "body": {"blob_content": {"raw": "x"}}}
        ]
    }
    with respx.mock(assert_all_called=True) as router:
        router.post(url).mock(return_value=httpx.Response(200, json=payload))
        resp = await api.get_link_metadata(GetLinkMetadataRequest(uuid="u"))
        assert len(resp.results) == 1
