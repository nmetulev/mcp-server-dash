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


def test_save_and_load_valid_token(tmp_path, monkeypatch):
    store = ts.DropboxTokenStore(base_dir=tmp_path)

    # Monkeypatch the dropbox client used by the module
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=True))

    store.save("abc")
    assert store.token_file.exists()
    assert json.loads(store.token_file.read_text())["access_token"] == "abc"

    # Fresh instance to test load
    store2 = ts.DropboxTokenStore(base_dir=tmp_path)
    assert store2.load() is True
    assert store2.is_authenticated is True
    assert store2.access_token == "abc"


def test_load_invalid_token_clears_state(tmp_path, monkeypatch):
    # Write an invalid token file
    token_file = tmp_path / "dropbox_token.json"
    token_file.write_text(json.dumps({"access_token": "bad"}))

    store = ts.DropboxTokenStore(base_dir=tmp_path)

    # Monkeypatch to raise AuthError on validation
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=False))

    assert store.load() is False
    assert store.is_authenticated is False
    # clear() should have removed the token file
    assert not token_file.exists()


def test_clear_removes_token_file(tmp_path):
    store = ts.DropboxTokenStore(base_dir=tmp_path)
    store.save("abc")
    assert store.token_file.exists()
    store.clear()
    assert not store.token_file.exists()
    assert store.is_authenticated is False
