"""
auth/authentication.py — registration, login, sessions and password recovery.

Framework-free: nothing here imports Streamlit, so the same functions can sit behind a
FastAPI router later.  The UI keeps the opaque session token (``start_session``) and asks
``user_for_session`` on each page load.

Security decisions (see docs/AUDIT_REPORT.md §8):
* salted PBKDF2 hashes; legacy SHA-256 hashes are upgraded transparently at next login;
* no accounts or passwords in source code — demo users come from the ``DEMO_USERS_JSON`` setting;
* password reset needs proof: a one-time code issued by a teacher/admin (30 min, stored hashed);
* teacher self-registration requires the configured invite code (feature is off if unset);
* login throttling per username (in-process; use a shared store when running several workers).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import timedelta

from auth import passwords, sessions
from auth.validation import (
    ValidationError,
    normalize_username,
    validate_full_name,
    validate_password,
    validate_username,
)
from config import get_settings
from database.connection import session_scope
from database.models import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, ROLES, PasswordResetToken, User, utcnow
from database.repository import UserRepository
from security.rate_limit import DatabaseRateLimiter, InProcessRateLimiter, RateLimitExceeded, shared_limits_enabled

logger = logging.getLogger("preluma.auth")

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
RESET_CODE_MINUTES = 30
_reset_issue_limiter = InProcessRateLimiter(3, 3600)
_shared_failure_limiter = DatabaseRateLimiter(MAX_FAILED_LOGINS, LOCKOUT_SECONDS)
_shared_reset_issue_limiter = DatabaseRateLimiter(3, 3600)


@dataclass(frozen=True)
class AuthUser:
    """Immutable, ORM-free view of a signed-in user."""

    id: int
    username: str
    role: str
    full_name: str

    @property
    def is_teacher(self) -> bool:
        return self.role in (ROLE_TEACHER, ROLE_ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN or self.username in get_settings().admin_usernames


def _to_auth_user(user: User) -> AuthUser:
    return AuthUser(id=user.id, username=user.username, role=user.role, full_name=user.full_name)


# ── throttling ───────────────────────────────────────────────────────────────
_failures: dict[str, list[float]] = {}
_failures_lock = threading.Lock()


def _recent_failures(key: str) -> list[float]:
    if shared_limits_enabled():
        return [0.0] * _shared_failure_limiter.count(f"auth-failure:{key}")
    cutoff = time.monotonic() - LOCKOUT_SECONDS
    with _failures_lock:
        recent = [t for t in _failures.get(key, []) if t > cutoff]
        _failures[key] = recent
        return recent


def _record_failure(key: str) -> None:
    if shared_limits_enabled():
        try:
            _shared_failure_limiter.check(f"auth-failure:{key}")
        except RateLimitExceeded:
            pass  # the over-limit failure was durably counted
        return
    with _failures_lock:
        _failures.setdefault(key, []).append(time.monotonic())


def _clear_failures(key: str) -> None:
    if shared_limits_enabled():
        _shared_failure_limiter.clear(f"auth-failure:{key}")
        return
    with _failures_lock:
        _failures.pop(key, None)


def reset_throttle() -> None:
    """Forget all failed attempts (used by tests)."""
    with _failures_lock:
        _failures.clear()
    _reset_issue_limiter.reset()


def is_locked(username: str) -> bool:
    return len(_recent_failures(normalize_username(username))) >= MAX_FAILED_LOGINS


# ── user creation ────────────────────────────────────────────────────────────
def create_user(username: str, password: str, full_name: str, role: str = ROLE_STUDENT) -> AuthUser:
    """Create an account (privileged: callers decide who may pick a role).

    Raises :class:`ValidationError` with a user-presentable message.
    """
    uname = validate_username(username)
    validate_password(password, uname)
    name = validate_full_name(full_name)
    if role not in ROLES:
        raise ValidationError("Unknown role.")
    with session_scope() as s:
        repo = UserRepository(s)
        if repo.get_by_username(uname):
            raise ValidationError("Username already taken. Please choose another.")
        user = repo.add(
            User(username=uname, password_hash=passwords.hash_password(password), role=role, full_name=name)
        )
        return _to_auth_user(user)


def register(username: str, password: str, full_name: str, role: str = ROLE_STUDENT) -> tuple[bool, str]:
    """Public self-registration.  Only *student* accounts can be created this way."""
    if role != ROLE_STUDENT:
        return False, "Teacher accounts need an invite code."
    try:
        create_user(username, password, full_name, ROLE_STUDENT)
    except ValidationError as exc:
        return False, str(exc)
    return True, "Account created successfully!"


def register_teacher(username: str, password: str, full_name: str, invite_code: str) -> tuple[bool, str]:
    """Teacher self-registration, guarded by the deployer's invite code."""
    expected = get_settings().teacher_invite_code
    if not expected:
        return False, "Teacher self-registration is disabled. Ask an administrator to create your account."
    if not hmac.compare_digest(str(invite_code or "").strip().encode(), expected.encode()):
        return False, "Invalid invite code. Contact your course admin for access."
    try:
        create_user(username, password, full_name, ROLE_TEACHER)
    except ValidationError as exc:
        return False, str(exc)
    return True, "Teacher account created! You can now log in."


def username_exists(username: str) -> bool:
    with session_scope() as s:
        return UserRepository(s).get_by_username(normalize_username(username)) is not None


# ── login ────────────────────────────────────────────────────────────────────
def login(username: str, password: str) -> tuple[AuthUser | None, str]:
    """Verify credentials.  Returns ``(user, "")`` or ``(None, reason)``."""
    uname = normalize_username(username)
    if not uname or not password:
        return None, "Please enter your username and password."
    if is_locked(uname):
        return None, "Too many failed attempts. Please wait a few minutes and try again."
    with session_scope() as s:
        repo = UserRepository(s)
        user = repo.get_by_username(uname)
        if user is None or not user.is_active:
            passwords.burn_time()
            _record_failure(uname)
            return None, "Incorrect username or password."
        if not passwords.verify_password(password, user.password_hash):
            _record_failure(uname)
            return None, "Incorrect username or password."
        if passwords.needs_rehash(user.password_hash):
            repo.set_password_hash(user, passwords.hash_password(password))  # silent upgrade
        repo.touch_login(user)
        _clear_failures(uname)
        return _to_auth_user(user), ""


def authenticate(username: str, password: str) -> AuthUser | None:
    """Convenience wrapper around :func:`login` that drops the failure reason."""
    return login(username, password)[0]


# ── sessions ─────────────────────────────────────────────────────────────────
def start_session(user: AuthUser) -> str:
    return sessions.create_session_token(user.id)


def user_for_session(token: str) -> AuthUser | None:
    user_id = sessions.resolve_session_token(token)
    if user_id is None:
        return None
    with session_scope() as s:
        user = UserRepository(s).get(user_id)
        return _to_auth_user(user) if user is not None and user.is_active else None


def end_session(token: str) -> None:
    sessions.revoke_session_token(token)


# ── password recovery / change ───────────────────────────────────────────────
def change_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
    """Self-service change; requires the current password."""
    uname = normalize_username(username)
    if is_locked(uname):
        return False, "Too many failed attempts. Please wait a few minutes."
    try:
        validate_password(new_password, uname)
    except ValidationError as exc:
        return False, str(exc)
    with session_scope() as s:
        repo = UserRepository(s)
        user = repo.get_by_username(uname)
        if user is None or not passwords.verify_password(current_password, user.password_hash):
            _record_failure(uname)
            return False, "Current password is incorrect."
        repo.set_password_hash(user, passwords.hash_password(new_password))
        user_id = user.id
    sessions.revoke_all_sessions(user_id)
    return True, "Password changed. Please log in again."


def issue_reset_code(actor_id: int, target_username: str) -> tuple[bool, str]:
    """A teacher/admin creates a one-time code for a user who forgot their password.

    Returns ``(True, code)`` — the actor hands the code to the user in person — or
    ``(False, reason)``.  Teachers may reset students; only admins may reset teachers/admins.
    """
    with session_scope() as s:
        repo = UserRepository(s)
        actor = repo.get(actor_id)
        target = repo.get_by_username(target_username)
        if actor is None or not actor.is_active or actor.role not in (ROLE_TEACHER, ROLE_ADMIN):
            return False, "Only teachers or administrators can issue reset codes."
        if target is None:
            return False, "Account not found."
        actor_is_admin = actor.role == ROLE_ADMIN or actor.username in get_settings().admin_usernames
        if target.role != ROLE_STUDENT and not actor_is_admin:
            return False, "Only an administrator can reset a teacher or admin account."
        try:
            limiter = _shared_reset_issue_limiter if shared_limits_enabled() else _reset_issue_limiter
            limiter.check(f"reset-issue:{actor.id}:{target.id}")
        except RateLimitExceeded:
            return False, "Too many reset codes issued. Please try again later."
        repo.invalidate_reset_tokens(target.id)
        code = secrets.token_urlsafe(6)
        repo.add_reset_token(
            PasswordResetToken(
                user_id=target.id,
                token_hash=hashlib.sha256(code.encode()).hexdigest(),
                issued_by=actor.id,
                expires_at=utcnow() + timedelta(minutes=RESET_CODE_MINUTES),
            )
        )
        return True, code


def reset_password_with_code(username: str, code: str, new_password: str) -> tuple[bool, str]:
    """Set a new password using a code from :func:`issue_reset_code`."""
    uname = normalize_username(username)
    throttle_key = f"reset:{uname}"
    if len(_recent_failures(throttle_key)) >= MAX_FAILED_LOGINS:
        return False, "Too many attempts. Please wait a few minutes."
    try:
        validate_password(new_password, uname)
    except ValidationError as exc:
        return False, str(exc)
    supplied = hashlib.sha256(str(code or "").strip().encode()).hexdigest()
    with session_scope() as s:
        repo = UserRepository(s)
        user = repo.get_by_username(uname)
        match = None
        if user is not None:
            for token in repo.valid_reset_tokens(user.id):
                if hmac.compare_digest(token.token_hash, supplied):
                    match = token
                    break
        if user is None or match is None:
            _record_failure(throttle_key)
            return False, "Invalid or expired reset code."
        match.used_at = utcnow()
        repo.set_password_hash(user, passwords.hash_password(new_password))
        user_id = user.id
    sessions.revoke_all_sessions(user_id)
    _clear_failures(throttle_key)
    return True, "Password reset successfully! You can now log in."


# ── optional demo accounts ───────────────────────────────────────────────────
def ensure_demo_users() -> int:
    """Create the accounts listed in ``DEMO_USERS_JSON`` that do not exist yet.

    Returns how many were created.  Never overwrites an existing account's password.
    """
    created = 0
    for entry in get_settings().demo_users:
        role = entry.get("role", ROLE_STUDENT)
        if role not in ROLES:
            logger.warning("Skipping demo user %r: unknown role %r", entry.get("username"), role)
            continue
        try:
            if not username_exists(entry["username"]):
                create_user(entry["username"], entry["password"], entry.get("full_name", entry["username"]), role)
                created += 1
        except ValidationError as exc:
            logger.warning("Skipping demo user %r: %s", entry.get("username"), exc)
    return created
