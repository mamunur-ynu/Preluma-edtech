"""
services/user_service.py — read-side use cases about people (rosters, display names).

Authentication itself lives in the ``auth`` package; this module answers questions such as
"who are the students?" for dashboards and the admin panel, returning plain dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from config import get_settings
from database.connection import session_scope
from database.models import ROLE_STUDENT
from database.repository import UserRepository


@dataclass(frozen=True)
class UserSummary:
    id: int
    username: str
    full_name: str
    role: str
    created_at: datetime
    last_login_at: datetime | None
    is_admin: bool
    student_number: int = 0          # 1-based position among students ("S001"), 0 for staff

    @property
    def display_id(self) -> str:
        return f"S{self.student_number:03d}" if self.student_number else ""

    @property
    def display_name(self) -> str:
        return f"{self.display_id} — {self.full_name}" if self.student_number else self.full_name


def list_users(role: str | None = None) -> list[UserSummary]:
    admins = get_settings().admin_usernames
    with session_scope() as s:
        everyone = UserRepository(s).list_by_role()
        numbers = {u.id: i for i, u in enumerate((u for u in everyone if u.role == ROLE_STUDENT), start=1)}
        return [
            UserSummary(
                id=u.id, username=u.username, full_name=u.full_name, role=u.role, created_at=u.created_at,
                last_login_at=u.last_login_at, is_admin=u.role == "admin" or u.username in admins,
                student_number=numbers.get(u.id, 0),
            )
            for u in everyone
            if role is None or u.role == role
        ]


def list_students() -> list[UserSummary]:
    return list_users(ROLE_STUDENT)


def get_user(username: str) -> UserSummary | None:
    uname = username.strip().lower()
    return next((u for u in list_users() if u.username == uname), None)


def get_user_by_id(user_id: int) -> UserSummary | None:
    return next((u for u in list_users() if u.id == user_id), None)


def student_number(username: str) -> int:
    """Sequential student number used for the S001-style label (0 if not a student)."""
    user = get_user(username)
    return user.student_number if user else 0


def student_display(username: str) -> str:
    user = get_user(username)
    return user.display_name if user else username


# ── administration ───────────────────────────────────────────────────────────
def set_active(actor_id: int, target_username: str, active: bool) -> tuple[bool, str]:
    """Deactivate (soft-delete) or re-activate an account.  Admins only; never yourself or another admin.

    Deactivation keeps the learning history (quiz attempts, progress) intact and revokes sessions.
    """
    from auth import sessions

    settings = get_settings()
    with session_scope() as s:
        repo = UserRepository(s)
        actor = repo.get(actor_id)
        target = repo.get_by_username(target_username)
        if actor is None or not (actor.role == "admin" or actor.username in settings.admin_usernames):
            return False, "Only administrators can change account status."
        if target is None:
            return False, "Account not found."
        if target.id == actor.id:
            return False, "You cannot change your own account."
        if target.role == "admin" or target.username in settings.admin_usernames:
            return False, "Administrator accounts are protected."
        target.is_active = active
        target_id = target.id
    if not active:
        sessions.revoke_all_sessions(target_id)
    return True, "Account re-activated." if active else "Account deactivated."


def is_admin_username(username: str) -> bool:
    """True for configured admins (``PRELUMA_ADMIN_USERS``) and for accounts with the admin role."""
    uname = (username or "").strip().lower()
    if not uname:
        return False
    if uname in get_settings().admin_usernames:
        return True
    user = get_user(uname)
    return bool(user and user.role == "admin")


def student_number_by_name(full_name: str) -> int:
    """Student number looked up by full name (legacy CSV stores identify students by name)."""
    target = " ".join(str(full_name).split()).casefold()
    return next((u.student_number for u in list_students() if u.full_name.casefold() == target), 0)
