"""
auth/sessions.py — server-side sessions with opaque tokens.

Why not a signed (stateless) token?  A signed token cannot be revoked and keeps trusting the
role it was issued with.  Here the browser only holds a random 256-bit token; the server keeps
its SHA-256 in ``user_sessions`` together with an expiry.  Logging out, disabling a user or a
password reset revokes sessions immediately, and the *current* role is always read from the
users table.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import update

from config import get_settings
from database.models import UserSession, utcnow
from database.repository import SessionRepository, UserRepository
from database.connection import session_scope


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session_token(user_id: int, ttl_seconds: int | None = None) -> str:
    """Create a session row and return the *plain* token (shown to the browser once)."""
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().session_ttl_seconds
    token = secrets.token_urlsafe(32)
    with session_scope() as s:
        SessionRepository(s).add(
            UserSession(
                user_id=user_id,
                token_hash=_hash_token(token),
                expires_at=utcnow() + timedelta(seconds=ttl),
            )
        )
    return token


def replace_session_token(user_id: int, previous_token: str | None = None) -> str:
    """Issue a login token and revoke the cookie it replaces in one transaction."""
    token = secrets.token_urlsafe(32)
    with session_scope() as s:
        if previous_token and len(previous_token) <= 200:
            SessionRepository(s).revoke(_hash_token(previous_token))
        SessionRepository(s).add(UserSession(
            user_id=user_id,
            token_hash=_hash_token(token),
            expires_at=utcnow() + timedelta(seconds=get_settings().session_ttl_seconds),
        ))
    return token


def resolve_session_token(token: str) -> int | None:
    """Return the ``user_id`` for a valid, unexpired, unrevoked, active-user token."""
    if not token or len(token) > 200:
        return None
    with session_scope() as s:
        row = SessionRepository(s).get_active(_hash_token(token))
        if row is None:
            return None
        user = UserRepository(s).get(row.user_id)
        if user is None or not user.is_active:
            return None
        return user.id


def revoke_session_token(token: str) -> None:
    if not token:
        return
    with session_scope() as s:
        SessionRepository(s).revoke(_hash_token(token))


def rotate_session_token(token: str) -> str | None:
    """Atomically consume one live token and issue its replacement.

    A competing rotation can consume the same old token only once because the
    conditional UPDATE is performed by the database before insertion.
    """
    if not token or len(token) > 200:
        return None
    now = utcnow()
    with session_scope() as s:
        user_id = s.scalar(
            update(UserSession)
            .where(
                UserSession.token_hash == _hash_token(token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .values(revoked_at=now)
            .returning(UserSession.user_id)
        )
        if user_id is None:
            return None
        user = UserRepository(s).get(user_id)
        if user is None or not user.is_active:
            return None
        replacement = secrets.token_urlsafe(32)
        SessionRepository(s).add(UserSession(
            user_id=user_id,
            token_hash=_hash_token(replacement),
            expires_at=now + timedelta(seconds=get_settings().session_ttl_seconds),
        ))
        return replacement


def revoke_all_sessions(user_id: int) -> None:
    with session_scope() as s:
        SessionRepository(s).revoke_all_for_user(user_id)
