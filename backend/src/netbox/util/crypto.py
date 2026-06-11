"""Encrypt and decrypt sensitive values persisted by the monitor."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def encryption_key_path_for_db(db_path: Path) -> Path:
    """Return the key file path associated with one SQLite database."""

    if str(db_path) == ":memory:":
        return Path(os.environ.get("NETBOX_ENCRYPTION_KEY_FILE", "/tmp/.netbox-test-key"))
    return db_path.parent / ".netbox-key"


def resolve_encryption_key(db_path: Path) -> bytes:
    """Load or create the Fernet key used to protect stored secrets."""

    env_key = os.environ.get("NETBOX_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode("utf-8")

    key_path = encryption_key_path_for_db(db_path)
    if key_path.is_file():
        return key_path.read_bytes().strip()

    key = Fernet.generate_key()
    if str(db_path) != ":memory:":
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        key_path.chmod(0o600)
    return key


def encrypt_secret(db_path: Path, value: str) -> str:
    """Encrypt one UTF-8 secret for SQLite storage."""

    if not value:
        return ""
    token = Fernet(resolve_encryption_key(db_path)).encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(db_path: Path, value: str) -> str:
    """Decrypt one stored secret value."""

    if not value:
        return ""
    try:
        raw = Fernet(resolve_encryption_key(db_path)).decrypt(value.encode("utf-8"))
    except InvalidToken as error:
        raise ValueError("Unable to decrypt stored SMTP credentials") from error
    return raw.decode("utf-8")
