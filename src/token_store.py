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


def get_default_token_dir() -> pathlib.Path:
    """Get a writable directory for token storage.
    
    Uses user's home directory/.mcp-server-dash/ which is guaranteed to be writable.
    Falls back to CWD if home directory is not accessible.
    """
    try:
        # Use user's home directory for reliable, writable storage
        home = pathlib.Path.home()
        token_dir = home / ".mcp-server-dash"
        token_dir.mkdir(parents=True, exist_ok=True)
        return token_dir
    except Exception as e:
        logger.warning(f"Could not use home directory for token storage: {e}, falling back to CWD")
        return pathlib.Path.cwd()


class DropboxTokenStore:
    """Handles persistence and validation of a Dropbox OAuth access token.

    Uses the system keyring for secure token storage. Falls back to reading
    from legacy file-based storage (`dropbox_token.json`).
    """

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        base = base_dir or get_default_token_dir()
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
        """Persist token to keyring (or file as fallback) and set in-memory state."""
        try:
            # Try to save to keyring first
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
            logger.debug("Token saved to keyring successfully")
        except Exception as e:
            # Fallback to file-based storage if keyring fails (common on Windows)
            logger.warning(f"Failed to save token to keyring: {e}, falling back to file storage")
            try:
                self._token_file.parent.mkdir(parents=True, exist_ok=True)
                with self._token_file.open("w") as f:
                    json.dump({"access_token": token}, f)
                # Set restrictive permissions on Windows (owner only)
                if hasattr(self._token_file, 'chmod'):
                    with suppress(Exception):
                        self._token_file.chmod(0o600)
                logger.info(f"Token saved to file: {self._token_file}")
            except Exception as file_error:
                logger.error(f"Failed to save token to file: {file_error}")
                raise RuntimeError(f"Failed to save token to keyring or file: {file_error}") from file_error
        
        self.access_token = token
        self.dbx = dropbox.Dropbox(token)


def main() -> None:
    """Interactive token management utility."""
    store = DropboxTokenStore()

    # Check if token exists
    token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)

    if not token:
        print("No token found in keyring.")
        return

    print(f"Token found in keyring (service: {KEYRING_SERVICE})")
    response = input("Do you want to remove the token? (y/N): ").strip().lower()

    if response == "y":
        store.clear()
        print("Token removed successfully.")
    else:
        print("Token not removed.")


if __name__ == "__main__":
    main()
