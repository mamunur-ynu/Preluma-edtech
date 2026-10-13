"""Authenticated encryption for uploaded text retained for index recovery.

Production/PostgreSQL workers must share one owner-managed key via environment.
Single-process SQLite demos use a private key file in the configured data dir;
the key and the database must be backed up together and never committed.
"""

from __future__ import annotations

import os
import stat
import time
import hmac

from cryptography.fernet import Fernet

from config import get_setting, get_settings

MAX_SOURCE_BYTES = 12 * 1024 * 1024


def _local_key() -> bytes:
    path = get_settings().data_dir / "document_recovery.key"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as handle:
            handle.write(Fernet.generate_key())
            handle.flush()
            os.fsync(handle.fileno())
    for _ in range(5):  # another local process may still be writing the new key
        if path.is_symlink():
            raise PermissionError("Document recovery key cannot be a symlink.")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise PermissionError("Document recovery key must be a private regular file (0600).")
        key = path.read_bytes().strip()
        if key:
            return key
        time.sleep(0.05)
    raise RuntimeError("Document recovery key file is empty.")


def document_cipher() -> Fernet:
    raw = get_setting("PRELUMA_DOCUMENT_KEY")
    if raw:
        key = raw.encode()
    elif get_settings().is_sqlite:
        key = _local_key()
    else:
        raise RuntimeError("PRELUMA_DOCUMENT_KEY is required for PostgreSQL document uploads/recovery.")
    try:
        return Fernet(key)
    except (TypeError, ValueError) as exc:
        raise ValueError("PRELUMA_DOCUMENT_KEY must be a valid Fernet key.") from exc


def encrypt_source(text: str, digest: str) -> bytes:
    payload = f"{digest}\n{text}".encode("utf-8")
    if len(payload) > MAX_SOURCE_BYTES:
        raise ValueError("Extracted document is too large to retain for recovery.")
    return document_cipher().encrypt(payload)


def decrypt_source(ciphertext: bytes, digest: str) -> str:
    saved_digest, separator, text = document_cipher().decrypt(ciphertext).decode("utf-8").partition("\n")
    if not separator or not hmac.compare_digest(saved_digest, digest):
        raise ValueError("Encrypted document does not match its metadata.")
    return text
