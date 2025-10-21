import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_server_dash
from auth_pkce import PKCEAuthFlow
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


# ========== PKCE Tests ==========


def test_generate_code_verifier():
    """Test that code_verifier generation produces valid PKCE verifiers."""
    flow = PKCEAuthFlow()
    verifier = flow._generate_code_verifier()

    # Per RFC 7636, verifier must be 43-128 characters
    assert 43 <= len(verifier) <= 128

    # Should only contain base64url characters
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in allowed_chars for c in verifier)

    # Should be different on each call (cryptographically random)
    verifier2 = flow._generate_code_verifier()
    assert verifier != verifier2


def test_generate_code_challenge():
    """Test that code_challenge is correctly computed from code_verifier."""
    flow = PKCEAuthFlow()
    verifier = "test_verifier_12345"
    challenge = flow._generate_code_challenge(verifier)

    # Manually compute expected challenge
    sha256_hash = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")

    assert challenge == expected

    # Should only contain base64url characters
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in allowed_chars for c in challenge)


@pytest.mark.asyncio
async def test_dash_get_auth_url_includes_pkce(monkeypatch):
    """Test that dash_get_auth_url generates URL with PKCE parameters."""
    # Set module-level APP_KEY
    monkeypatch.setattr(mcp_server_dash, "APP_KEY", "test_app_key")

    # Reset module-level state
    mcp_server_dash.pkce_flow._code_verifier = None

    url_output = await mcp_server_dash.dash_get_auth_url()

    # Check that code_verifier was stored
    assert mcp_server_dash.pkce_flow._code_verifier is not None
    assert len(mcp_server_dash.pkce_flow._code_verifier) >= 43

    # Check that URL contains PKCE parameters
    assert "code_challenge=" in url_output
    assert "code_challenge_method=S256" in url_output
    assert "client_id=test_app_key" in url_output

    # Verify the code_challenge matches the stored verifier
    stored_verifier = mcp_server_dash.pkce_flow._code_verifier
    expected_challenge = mcp_server_dash.pkce_flow._generate_code_challenge(stored_verifier)
    assert f"code_challenge={expected_challenge}" in url_output


@pytest.mark.asyncio
async def test_dash_authenticate_requires_code_verifier(monkeypatch):
    """Test that dash_authenticate fails if code_verifier is not set."""
    monkeypatch.setattr(mcp_server_dash, "APP_KEY", "test_app_key")

    # Clear code_verifier
    mcp_server_dash.pkce_flow._code_verifier = None

    result = await mcp_server_dash.dash_authenticate("dummy_code")

    assert "No PKCE code_verifier found" in result
    assert "generate_auth_url first" in result


@pytest.mark.asyncio
async def test_dash_authenticate_includes_code_verifier(monkeypatch):
    """Test that dash_authenticate includes code_verifier in token exchange."""
    monkeypatch.setattr(mcp_server_dash, "APP_KEY", "test_app_key")

    # Set up code_verifier
    test_verifier = "test_verifier_12345_abcdefghijklmnopqrstuv"
    mcp_server_dash.pkce_flow._code_verifier = test_verifier

    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "test_token_123"}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    # Mock Dropbox client
    mock_dbx = MagicMock()
    mock_account = MagicMock()
    mock_account.name.display_name = "Test User"
    mock_account.email = "test@example.com"
    mock_dbx.users_get_current_account.return_value = mock_account

    # Mock token store
    mock_token_store = MagicMock()
    mock_token_store.save = MagicMock()

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch.object(mcp_server_dash.dropbox, "Dropbox", return_value=mock_dbx),
    ):
        monkeypatch.setattr(mcp_server_dash, "token_store", mock_token_store)

        result = await mcp_server_dash.dash_authenticate("auth_code_123")

    # Verify the token exchange request included code_verifier
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://api.dropboxapi.com/oauth2/token"
    assert call_args[1]["data"]["code_verifier"] == test_verifier
    assert call_args[1]["data"]["code"] == "auth_code_123"
    assert call_args[1]["data"]["client_id"] == "test_app_key"

    # Verify code_verifier was cleared after use
    assert mcp_server_dash.pkce_flow._code_verifier is None

    # Verify success message
    assert "Successfully authenticated" in result
    assert "Test User" in result


@pytest.mark.asyncio
async def test_dash_authenticate_clears_verifier_on_error(monkeypatch):
    """Test that code_verifier is cleared even when authentication fails."""
    monkeypatch.setattr(mcp_server_dash, "APP_KEY", "test_app_key")

    # Set up code_verifier
    test_verifier = "test_verifier_error_case"
    mcp_server_dash.pkce_flow._code_verifier = test_verifier

    # Mock httpx client to return error
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": "invalid_grant", "error_description": "Invalid auth code"}'
    mock_response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "Invalid auth code",
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await mcp_server_dash.dash_authenticate("bad_auth_code")

    # Verify code_verifier was cleared even though auth failed
    assert mcp_server_dash.pkce_flow._code_verifier is None

    # Verify error message
    assert "Authentication failed" in result


@pytest.mark.asyncio
async def test_pkce_full_flow(monkeypatch):
    """Integration test: full OAuth flow with PKCE from URL generation to authentication."""
    monkeypatch.setattr(mcp_server_dash, "APP_KEY", "test_app_key")

    # Clear initial state
    mcp_server_dash.pkce_flow._code_verifier = None

    # Step 1: Get auth URL
    url_output = await mcp_server_dash.dash_get_auth_url()
    assert "code_challenge=" in url_output

    # Capture the code_verifier that was generated
    stored_verifier = mcp_server_dash.pkce_flow._code_verifier
    assert stored_verifier is not None

    # Step 2: Simulate user authorization and authenticate
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "final_token"}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_dbx = MagicMock()
    mock_account = MagicMock()
    mock_account.name.display_name = "Integration Test User"
    mock_account.email = "integration@test.com"
    mock_dbx.users_get_current_account.return_value = mock_account

    mock_token_store = MagicMock()
    mock_token_store.save = MagicMock()

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch.object(mcp_server_dash.dropbox, "Dropbox", return_value=mock_dbx),
    ):
        monkeypatch.setattr(mcp_server_dash, "token_store", mock_token_store)

        result = await mcp_server_dash.dash_authenticate("auth_code_xyz")

    # Verify the stored verifier was used in the token exchange
    call_args = mock_client.post.call_args
    assert call_args[1]["data"]["code_verifier"] == stored_verifier

    # Verify authentication succeeded
    assert "Successfully authenticated" in result

    # Verify code_verifier was cleared
    assert mcp_server_dash.pkce_flow._code_verifier is None
