"""
auth/passwords.py — password hashing with the standard library only.

Format of a stored hash::

    pbkdf2_sha256$<iterations>$<salt, urlsafe-base64>$<derived key, urlsafe-base64>

* PBKDF2-HMAC-SHA256 with a random 16-byte salt per password (OWASP-recommended 600 000
  iterations by default; override with ``PRELUMA_PBKDF2_ITERATIONS`` — tests use a small value).
* **Legacy support:** the first version of Preluma stored unsalted ``sha256(password)`` as 64
  hex characters.  :func:`verify_password` still accepts those and :func:`needs_rehash` tells
  the caller to upgrade the stored value after a successful login, so users migrate silently.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000
_LEGACY_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _iterations() -> int:
    try:
        return max(1_000, int(os.environ.get("PRELUMA_PBKDF2_ITERATIONS", DEFAULT_ITERATIONS)))
    except ValueError:
        return DEFAULT_ITERATIONS


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash string for ``password``."""
    iterations = _iterations()
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash (new or legacy format)."""
    if not stored:
        return False
    if _LEGACY_SHA256.match(stored):
        candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate, stored)
    try:
        algorithm, iterations_text, salt_text, key_text = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = _unb64(key_text)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(salt_text), int(iterations_text)
        )
        return hmac.compare_digest(candidate, expected)
    except (ValueError, TypeError):
        return False


def needs_rehash(stored: str) -> bool:
    """True for legacy hashes and for hashes made with fewer iterations than today's default."""
    if _LEGACY_SHA256.match(stored or ""):
        return True
    try:
        _, iterations_text, _, _ = stored.split("$")
        return int(iterations_text) < _iterations()
    except (ValueError, TypeError):
        return True


# A pre-computed hash used to burn the same CPU time when the username does not exist,
# so response time does not reveal which usernames are registered.
_DUMMY_HASH: str | None = None


def burn_time() -> None:
    """Spend one hash verification of CPU (timing-attack mitigation)."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("preluma-dummy-password")
    verify_password("wrong-password", _DUMMY_HASH)
