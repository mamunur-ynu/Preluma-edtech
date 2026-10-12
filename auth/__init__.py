"""Authentication package (framework-independent)."""

from auth.authentication import (
    AuthUser,
    authenticate,
    change_password,
    create_user,
    end_session,
    ensure_demo_users,
    issue_reset_code,
    login,
    register,
    register_teacher,
    reset_password_with_code,
    start_session,
    user_for_session,
    username_exists,
)
from auth.validation import ValidationError, esc, sanitize_text

__all__ = [
    "AuthUser",
    "ValidationError",
    "authenticate",
    "change_password",
    "create_user",
    "end_session",
    "ensure_demo_users",
    "esc",
    "issue_reset_code",
    "login",
    "register",
    "register_teacher",
    "reset_password_with_code",
    "sanitize_text",
    "start_session",
    "user_for_session",
    "username_exists",
]
