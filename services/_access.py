"""Small server-side account checks shared by service use cases."""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import User
from database.repository import UserRepository


def require_active_user(session: Session, user_id: int) -> User:
    """Reject missing or disabled accounts before any private service operation."""
    user = UserRepository(session).get(user_id) if isinstance(user_id, int) else None
    if user is None or not user.is_active:
        raise PermissionError("An active account is required.")
    return user
