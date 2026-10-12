"""Small helpers shared by the test modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"


def app_source() -> str:
    """All UI source text (entry point + pages + components) for the "does the UI still contain X" tests."""
    parts = [APP_FILE, ROOT / "streamlit_app.py"]
    for folder in ("views", "components"):
        parts.extend(sorted((ROOT / folder).glob("*.py")))
    return "\n".join(p.read_text(encoding="utf-8") for p in parts if p.exists())


def logged_in_app(role: str = "student", page: str = "Home"):
    """An ``AppTest`` that starts already signed in as a freshly created user of ``role``."""
    from streamlit.testing.v1 import AppTest

    from auth import create_user, ensure_demo_users, start_session  # noqa: F401
    from services.course_service import ensure_default_catalog

    ensure_default_catalog()
    user = create_user(f"{role}_tester", "Passw0rd!xyz", f"Test {role.title()}", role)
    at = AppTest.from_file(str(APP_FILE), default_timeout=60)
    at.session_state["logged_in"] = True
    at.session_state["_session_token"] = start_session(user)
    at.session_state["user_id"] = user.id
    at.session_state["user_role"] = "teacher" if role == "admin" else role
    at.session_state["username"] = user.username
    at.session_state["student"] = user.full_name
    at.session_state["is_admin"] = user.is_admin
    at.session_state["active_page"] = page
    at.session_state["_page_restored"] = True
    return at.run()
