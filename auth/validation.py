"""
auth/validation.py — input validation and output escaping.

Every value that comes from a person (registration form, chat box, homework title…)
should pass through one of these helpers before it is stored or rendered.
"""

from __future__ import annotations

import html
import re

_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class ValidationError(ValueError):
    """Raised with a message that is safe to show directly to the user."""


def normalize_username(username: str) -> str:
    return str(username or "").strip().lower()


def validate_username(username: str) -> str:
    """Return the normalised username or raise :class:`ValidationError`."""
    uname = normalize_username(username)
    if not uname:
        raise ValidationError("Username is required.")
    if not _USERNAME_RE.match(uname):
        raise ValidationError(
            "Username must be 3–32 characters: lowercase letters, digits, '.', '_' or '-', "
            "starting with a letter or digit."
        )
    return uname


def validate_password(password: str, username: str = "") -> str:
    """Enforce a basic, student-friendly password policy."""
    password = str(password or "")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        raise ValidationError("Password must contain at least one letter and one digit.")
    if username and password.lower() == normalize_username(username):
        raise ValidationError("Password must not be the same as the username.")
    return password


def sanitize_text(text: str, max_length: int = 500) -> str:
    """Strip control characters, collapse surrounding whitespace and cap the length."""
    cleaned = _CONTROL_CHARS.sub("", str(text or "")).strip()
    return cleaned[:max_length]


def validate_full_name(full_name: str) -> str:
    name = " ".join(sanitize_text(full_name, 80).split())
    if len(name) < 2:
        raise ValidationError("Please enter your full name (at least 2 characters).")
    if "<" in name or ">" in name:
        raise ValidationError("Names cannot contain '<' or '>'.")
    return name


def esc(value: object) -> str:
    """HTML-escape anything before interpolating it into ``unsafe_allow_html`` markup."""
    return html.escape(str(value if value is not None else ""), quote=True)
