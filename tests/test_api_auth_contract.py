"""Private BFF credential exchange and atomic session lifecycle, using synthetic users."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from api.app import app
from auth import create_user
from auth.sessions import resolve_session_token
from database.connection import session_scope
from database.models import User, UserSession, utcnow

KEY = "synthetic-private-bff-key-for-auth-tests-12345"
PASSWORD = "Passw0rd!xyz"


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {"X-Preluma-BFF-Key": KEY}
    if token:
        headers["X-Preluma-Session"] = token
    return headers


def test_auth_routes_are_private_no_store_and_do_not_enumerate(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    create_user("auth-user", PASSWORD, "Auth User")
    with TestClient(app) as client:
        payload = {"username": "auth-user", "password": PASSWORD}
        assert client.post("/v1/auth/login", json=payload).status_code == 401
        assert client.post("/v1/auth/login", headers={"X-Preluma-BFF-Key": "wrong"}, json=payload).status_code == 401
        unknown = client.post("/v1/auth/login", headers=_headers(), json={**payload, "username": "absent"})
        wrong = client.post("/v1/auth/login", headers=_headers(), json={**payload, "password": "wrong"})
        assert (unknown.status_code, unknown.json()) == (wrong.status_code, wrong.json())
        success = client.post("/v1/auth/login", headers=_headers(), json=payload)
        assert success.status_code == 200
        assert success.headers["cache-control"] == "no-store"
        assert set(success.json()) == {"session_token", "expires_in_seconds"}
        token = success.json()["session_token"]
        assert token not in str(success.headers)
        assert client.get("/v1/me", headers=_headers(token)).json()["username"] == "auth-user"


def test_rotation_consumes_old_token_and_logout_is_idempotent(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    create_user("rotate-user", PASSWORD, "Rotate User")
    with TestClient(app) as client:
        old = client.post("/v1/auth/login", headers=_headers(), json={
            "username": "rotate-user", "password": PASSWORD,
        }).json()["session_token"]
        rotated = client.post("/v1/auth/rotate", headers=_headers(old))
        assert rotated.status_code == 200
        new = rotated.json()["session_token"]
        assert new != old
        assert resolve_session_token(old) is None
        assert resolve_session_token(new) is not None
        assert client.post("/v1/auth/rotate", headers=_headers(old)).status_code == 401
        assert client.post("/v1/auth/logout", headers=_headers(new)).status_code == 204
        assert client.post("/v1/auth/logout", headers=_headers(new)).status_code == 204
        assert client.get("/v1/me", headers=_headers(new)).status_code == 401


def test_new_login_replaces_previous_browser_session(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    create_user("relogin-user", PASSWORD, "Relogin User")
    payload = {"username": "relogin-user", "password": PASSWORD}
    with TestClient(app) as client:
        old = client.post("/v1/auth/login", headers=_headers(), json=payload).json()["session_token"]
        replacement = client.post("/v1/auth/login", headers=_headers(old), json=payload)
        assert replacement.status_code == 200
        new = replacement.json()["session_token"]
        assert new != old
        assert resolve_session_token(old) is None
        assert resolve_session_token(new) is not None


def test_expired_or_deactivated_session_cannot_rotate(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    user = create_user("expire-user", PASSWORD, "Expire User")
    with TestClient(app) as client:
        token = client.post("/v1/auth/login", headers=_headers(), json={
            "username": "expire-user", "password": PASSWORD,
        }).json()["session_token"]
        with session_scope() as session:
            row = session.scalar(select(UserSession).where(UserSession.user_id == user.id))
            row.expires_at = utcnow() - timedelta(seconds=1)
        assert client.post("/v1/auth/rotate", headers=_headers(token)).status_code == 401
        fresh = client.post("/v1/auth/login", headers=_headers(), json={
            "username": "expire-user", "password": PASSWORD,
        }).json()["session_token"]
        with session_scope() as session:
            session.get(User, user.id).is_active = False
        assert client.post("/v1/auth/rotate", headers=_headers(fresh)).status_code == 401
        assert client.get("/v1/me", headers=_headers(fresh)).status_code == 401
