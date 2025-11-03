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


async def _execute_search_and_get_body(req: DashSearchRequest):
    """Helper to execute search request and return parsed request body."""
    import json

    api = DashAPI("token")
    url = "https://api.dropboxapi.com/2/dcs/search_mcp"
    payload = {"results": []}

    with respx.mock(assert_all_called=True) as router:
        mock_route = router.post(url).mock(return_value=httpx.Response(200, json=payload))
        await api.search(req)
        request_body = mock_route.calls.last.request.content
        return json.loads(request_body)


@pytest.mark.asyncio
async def test_search_with_connector_filter():
    """Test that connector_id filter is properly included in the request."""
    req = DashSearchRequest(query_text="test", connector_id="slack")
    body = await _execute_search_and_get_body(req)

    assert len(body["filters"]) == 1
    assert body["filters"][0]["filter"][".tag"] == "connector_filter"
    assert body["filters"][0]["filter"]["connector_id"] == "slack"


@pytest.mark.asyncio
async def test_search_with_time_range_filter():
    """Test that start_datetime and end_datetime filters are properly included."""
    start_time = "2025-10-30T16:24:12.071Z"
    end_time = "2025-10-31T16:24:12.071Z"

    req = DashSearchRequest(query_text="test", start_datetime=start_time, end_datetime=end_time)
    body = await _execute_search_and_get_body(req)

    assert len(body["filters"]) == 1
    time_filter = body["filters"][0]["filter"]
    assert time_filter[".tag"] == "time_range_filter"
    assert time_filter["start_datetime"] == start_time
    assert time_filter["end_datetime"] == end_time


@pytest.mark.asyncio
async def test_search_with_multiple_filters():
    """Test that multiple filters can be combined (file_type + connector + time_range)."""
    req = DashSearchRequest(
        query_text="test",
        file_type="pdf",
        connector_id="google_drive",
        start_datetime="2025-10-30T00:00:00.000Z",
    )
    body = await _execute_search_and_get_body(req)

    assert len(body["filters"]) == 3
    filter_tags = [f["filter"][".tag"] for f in body["filters"]]
    assert "file_type_filter" in filter_tags
    assert "connector_filter" in filter_tags
    assert "time_range_filter" in filter_tags
    assert body["search_vertical"] == {".tag": "multimedia"}


@pytest.mark.asyncio
async def test_search_with_file_type_sets_multimedia_vertical():
    """Test that file_type filter adds multimedia search vertical."""
    req = DashSearchRequest(query_text="test", file_type="image")
    body = await _execute_search_and_get_body(req)

    assert body["search_vertical"] == {".tag": "multimedia"}
    assert body["filters"][0]["filter"]["file_type"] == "image"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start_time,end_time",
    [
        ("2025-10-30T00:00:00.000Z", None),
        (None, "2025-10-31T23:59:59.999Z"),
    ],
)
async def test_search_with_partial_time_range(start_time, end_time):
    """Test that time range filter works with only start_datetime or end_datetime."""
    req = DashSearchRequest(query_text="test", start_datetime=start_time, end_datetime=end_time)
    body = await _execute_search_and_get_body(req)

    time_filter = body["filters"][0]["filter"]
    assert time_filter[".tag"] == "time_range_filter"

    if start_time:
        assert time_filter["start_datetime"] == start_time
        assert "end_datetime" not in time_filter
    else:
        assert time_filter["end_datetime"] == end_time
        assert "start_datetime" not in time_filter
