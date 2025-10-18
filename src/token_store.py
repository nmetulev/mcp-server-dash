"""Token persistence and validation for Dropbox OAuth access tokens."""

from __future__ import annotations

import json
import logging
import pathlib
from contextlib import suppress

import dropbox
import keyring

logger = logging.getLogger(__name__)

# Keyring service name for storing Dropbox tokens
KEYRING_SERVICE = "mcp-server-dash"
KEYRING_USERNAME = "dropbox_access_token"


class DropboxTokenStore:
    """Handles persistence and validation of a Dropbox OAuth access token.

    Uses the system keyring for secure token storage. Falls back to reading
    from legacy file-based storage (`dropbox_token.json`).
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
        """Clear any saved token from keyring and delete legacy token files."""
        self.access_token = None
        self.dbx = None
        # Remove from keyring
        with suppress(Exception):
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        # Remove legacy file-based tokens
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
        """Load token from keyring (or legacy file storage) and validate it.

        Returns True if a valid token is loaded, else False.
        """
        try:
            token = None
            # Primary: Load from keyring
            token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)

            # Fallback: local dropbox_token.json in CWD
            if not token and self._token_file.exists():
                token = self._read_token_file(self._token_file)
                if token:
                    logger.info("Migrating token from legacy file to keyring")

            if not token:
                return False

            # Validate token by calling current account
            dbx = dropbox.Dropbox(token)
            dbx.users_get_current_account()
            self.access_token = token
            self.dbx = dbx

            # If loaded from legacy file, save to keyring and remove file
            if self._token_file.exists():
                self.save(token)
                with suppress(Exception):
                    self._token_file.unlink(missing_ok=True)

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
        """Persist token to keyring and set in-memory state."""
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        self.access_token = token
        self.dbx = dropbox.Dropbox(token)
