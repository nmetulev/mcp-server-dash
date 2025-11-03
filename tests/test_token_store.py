import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import token_store as ts


class FakeDropbox:
    def __init__(self, token: str, *, valid: bool = True):
        self.token = token
        self._valid = valid

    def users_get_current_account(self):
        if not self._valid:
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


def setup_store(tmp_path, monkeypatch, keyring_available=True):
    """Helper to setup store with fake keyring and dropbox."""
    fake_keyring = FakeKeyring()
    monkeypatch.setattr(ts, "keyring", fake_keyring)
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=True))

    if not keyring_available:
        fake_keyring.set_password = Mock(side_effect=RuntimeError("Keyring unavailable"))

    return ts.DropboxTokenStore(base_dir=tmp_path), fake_keyring


def test_save_and_load_valid_token(tmp_path, monkeypatch):
    store, keyring = setup_store(tmp_path, monkeypatch)

    store.save("abc")
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "abc"
    assert not store.token_file.exists()

    store2 = ts.DropboxTokenStore(base_dir=tmp_path)
    assert store2.load()
    assert store2.is_authenticated
    assert store2.access_token == "abc"


def test_load_invalid_token_clears_state(tmp_path, monkeypatch):
    store, keyring = setup_store(tmp_path, monkeypatch)
    keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "bad_token")
    monkeypatch.setattr(ts.dropbox, "Dropbox", lambda token: FakeDropbox(token, valid=False))

    assert not store.load()
    assert not store.is_authenticated
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None


def test_clear_removes_token_from_keyring(tmp_path, monkeypatch):
    store, keyring = setup_store(tmp_path, monkeypatch)

    store.save("abc")
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "abc"

    store.clear()
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None
    assert not store.is_authenticated


def test_load_from_file(tmp_path, monkeypatch):
    store, _ = setup_store(tmp_path, monkeypatch)
    (tmp_path / "dropbox_token.json").write_text(json.dumps({"access_token": "file_token"}))

    assert store.load()
    assert store.access_token == "file_token"


def test_load_no_token_exists(tmp_path, monkeypatch):
    store, _ = setup_store(tmp_path, monkeypatch)

    assert not store.load()
    assert not store.is_authenticated


def test_save_fallback_to_file(tmp_path, monkeypatch):
    store, _ = setup_store(tmp_path, monkeypatch, keyring_available=False)

    store.save("fallback_token")

    assert store.token_file.exists()
    assert json.loads(store.token_file.read_text())["access_token"] == "fallback_token"
    assert store.access_token == "fallback_token"


def test_save_both_keyring_and_file_fail(tmp_path, monkeypatch):
    store, _ = setup_store(tmp_path, monkeypatch, keyring_available=False)
    tmp_path.chmod(0o400)

    try:
        with pytest.raises(RuntimeError, match="Failed to save token"):
            store.save("test_token")
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.parametrize(
    "content,reason",
    [
        ("not valid json {", "corrupt JSON"),
        (json.dumps({"other_key": "value"}), "missing access_token key"),
        (json.dumps({"access_token": ""}), "empty access_token"),
    ],
)
def test_read_token_file_invalid(tmp_path, content, reason):
    store = ts.DropboxTokenStore(base_dir=tmp_path)
    store.token_file.write_text(content)

    assert store._read_token_file(store.token_file) is None


def test_load_generic_exception(tmp_path, monkeypatch):
    store, keyring = setup_store(tmp_path, monkeypatch)
    keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "test_token")
    monkeypatch.setattr(
        ts.dropbox, "Dropbox", lambda token: (_ for _ in ()).throw(Exception("Error"))
    )

    assert not store.load()
    assert not store.is_authenticated
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None


def test_clear_removes_file_token(tmp_path, monkeypatch):
    store, _ = setup_store(tmp_path, monkeypatch)
    store.token_file.write_text(json.dumps({"access_token": "file_token"}))

    store.clear()

    assert not store.token_file.exists()
    assert not store.is_authenticated


def test_token_file_property(tmp_path):
    store = ts.DropboxTokenStore(base_dir=tmp_path)
    assert store.token_file == tmp_path / "dropbox_token.json"


def test_get_default_token_dir_fallback(monkeypatch):
    monkeypatch.setattr(ts.pathlib.Path, "home", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert ts.get_default_token_dir() == ts.pathlib.Path.cwd()


def setup_interactive_test(tmp_path, monkeypatch, user_input="y"):
    """Helper to setup interactive clearing tests."""
    keyring = FakeKeyring()
    monkeypatch.setattr(ts, "keyring", keyring)
    monkeypatch.setattr(ts, "get_default_token_dir", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: user_input)
    return keyring, tmp_path / "dropbox_token.json"


def test_clear_token_interactive_no_token(tmp_path, monkeypatch, capsys):
    setup_interactive_test(tmp_path, monkeypatch)
    ts.clear_token_interactive()
    assert "No token found" in capsys.readouterr().out


def test_clear_token_interactive_keyring_confirm(tmp_path, monkeypatch, capsys):
    keyring, _ = setup_interactive_test(tmp_path, monkeypatch, "y")
    keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "test_token")

    ts.clear_token_interactive()

    out = capsys.readouterr().out
    assert "Token found in keyring" in out
    assert "Token removed successfully" in out
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None


def test_clear_token_interactive_keyring_decline(tmp_path, monkeypatch, capsys):
    keyring, _ = setup_interactive_test(tmp_path, monkeypatch, "n")
    keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "test_token")

    ts.clear_token_interactive()

    out = capsys.readouterr().out
    assert "Token found in keyring" in out
    assert "Token not removed" in out
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) == "test_token"


def test_clear_token_interactive_file(tmp_path, monkeypatch, capsys):
    _, token_file = setup_interactive_test(tmp_path, monkeypatch, "y")
    token_file.write_text(json.dumps({"access_token": "file_token"}))

    ts.clear_token_interactive()

    out = capsys.readouterr().out
    assert "Token found in file" in out
    assert str(token_file) in out
    assert "Token removed successfully" in out
    assert not token_file.exists()


def test_clear_token_interactive_both(tmp_path, monkeypatch, capsys):
    keyring, token_file = setup_interactive_test(tmp_path, monkeypatch, "y")
    keyring.set_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME, "keyring_token")
    token_file.write_text(json.dumps({"access_token": "file_token"}))

    ts.clear_token_interactive()

    out = capsys.readouterr().out
    assert "Token found in keyring" in out
    assert "Token found in file" in out
    assert "Token removed successfully" in out
    assert keyring.get_password(ts.KEYRING_SERVICE, ts.KEYRING_USERNAME) is None
    assert not token_file.exists()
