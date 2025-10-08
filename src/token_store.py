"""Token persistence and validation for Dropbox OAuth access tokens."""

from __future__ import annotations

import json
import logging
import pathlib
from contextlib import suppress

import dropbox

logger = logging.getLogger(__name__)


class DropboxTokenStore:
    """Handles persistence and validation of a Dropbox OAuth access token.

    Default location: a local file named `dropbox_token.json` in the current
    working directory. Falls back to reading from `./data/dropbox_token.json`
    for backward compatibility when loading.
    """

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        base = base_dir or pathlib.Path.cwd()
        self._token_file = base / "dropbox_token.json"
        self.access_token: str | None = None
        self.dbx: dropbox.Dropbox | None = None

    @property
    def token_file(self) -> pathlib.Path:
        return self._token_file

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token and self.dbx)

    def clear(self) -> None:
        """Clear any saved token and delete the token file."""
        self.access_token = None
        self.dbx = None
        with suppress(Exception):
            self._token_file.unlink(missing_ok=True)

    def _read_token_file(self, path: pathlib.Path) -> str | None:
        try:
            with path.open("r") as f:
                data = json.load(f)
            token = data.get("access_token")
            return token if token else None
        except Exception:
            return None

    def load(self) -> bool:
        """Load token from disk and validate it.

        Returns True if a valid token is loaded, else False.
        """
        try:
            token = None
            # Preferred location: local dropbox_token.json in CWD
            if self._token_file.exists():
                token = self._read_token_file(self._token_file)
            # Fallback: historical location ./data/dropbox_token.json
            if not token:
                legacy = pathlib.Path.cwd() / "data" / "dropbox_token.json"
                if legacy.exists():
                    token = self._read_token_file(legacy)
            if not token:
                return False
            # Validate token by calling current account
            dbx = dropbox.Dropbox(token)
            dbx.users_get_current_account()
            self.access_token = token
            self.dbx = dbx
            return True
        except dropbox.exceptions.AuthError as e:
            logger.warning("Invalid/expired Dropbox token found on load: %s", e)
            self.clear()
            return False
        except Exception:
            # Any failure -> clear state and remove corrupted/invalid token
            self.clear()
            return False

    def save(self, token: str) -> None:
        """Persist token to disk and set in-memory state."""
        with self._token_file.open("w") as f:
            json.dump({"access_token": token}, f)
        self.access_token = token
        self.dbx = dropbox.Dropbox(token)
