import json
from pathlib import Path

from dash_api import DashSearchResponse, GetLinkMetadataResponse

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_parse_search_response_success():
    data = load_json("search_success.json")
    obj = DashSearchResponse(**data)
    assert len(obj.results) == 1
    r = obj.results[0].query_result
    assert r is not None
    assert r.title == "Doc Title"
    assert r.url == "https://example.com/doc"


def test_parse_link_metadata_success():
    data = load_json("link_metadata_success.json")
    obj = GetLinkMetadataResponse(**data)
    assert len(obj.results) == 1
    m = obj.results[0]
    assert m.title == "File Title"
    assert m.mime_type == "text/plain"
