import json
from types import SimpleNamespace

import token_store as ts


class FakeDropbox:
    def __init__(self, token: str, *, valid: bool = True):
        self.token = token
        self._valid = valid

    def users_get_current_account(self):
        if not self._valid:
            # Mimic the dropbox AuthError signature with minimal attributes
            raise ts.dropbox.exceptions.AuthError("request_id", "invalid_token")
        return SimpleNamespace(name=SimpleNamespace(display_name="Test"), email="e@example.com")


class FakeKeyring:
    """Mock keyring for testing."""

    def __init__(self):
        self._store = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


def test_save_and_load_valid_token(tmp_path, monkeypatch):
    fake_keyring = FakeKeyring()
    store = ts.DropboxTokenStore(base_dir=tmp_path)

    # Monkeypatch both keyring and dropbox client
    monkeypatch.setattr(ts, "keyring", fake_keyring)
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=True))

    store.save("abc")
    # Verify token is stored in keyring (not file)
    assert fake_keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "abc"
    assert not store.token_file.exists()

    # Fresh instance to test load
    store2 = ts.DropboxTokenStore(base_dir=tmp_path)
    monkeypatch.setattr(ts, "keyring", fake_keyring)
    assert store2.load() is True
    assert store2.is_authenticated is True
    assert store2.access_token == "abc"


def test_load_invalid_token_clears_state(tmp_path, monkeypatch):
    fake_keyring = FakeKeyring()
    # Store an invalid token in keyring
    fake_keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "bad")

    store = ts.DropboxTokenStore(base_dir=tmp_path)

    # Monkeypatch to raise AuthError on validation
    monkeypatch.setattr(ts, "keyring", fake_keyring)
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=False))

    assert store.load() is False
    assert store.is_authenticated is False
    # clear() should have removed the token from keyring
    assert fake_keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None


def test_clear_removes_token_from_keyring(tmp_path, monkeypatch):
    fake_keyring = FakeKeyring()
    store = ts.DropboxTokenStore(base_dir=tmp_path)

    monkeypatch.setattr(ts, "keyring", fake_keyring)

    store.save("abc")
    assert fake_keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "abc"

    store.clear()
    assert fake_keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None
    assert store.is_authenticated is False


def test_migration_from_legacy_file(tmp_path, monkeypatch):
    """Test that tokens are migrated from legacy file storage to keyring."""
    fake_keyring = FakeKeyring()

    # Create a legacy token file
    token_file = tmp_path / "dropbox_token.json"
    token_file.write_text(json.dumps({"access_token": "legacy_token"}))

    store = ts.DropboxTokenStore(base_dir=tmp_path)
    monkeypatch.setattr(ts, "keyring", fake_keyring)
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=True))

    # Load should migrate the token
    assert store.load() is True
    assert store.access_token == "legacy_token"

    # Token should now be in keyring
    assert fake_keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "legacy_token"

    # Legacy file should be removed
    assert not token_file.exists()
