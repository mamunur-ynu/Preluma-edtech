"""The new read-only boundary must not bypass Streamlit's service authorization."""

from fastapi.testclient import TestClient

from api.app import app
from auth import create_user
from auth.sessions import create_session_token, revoke_session_token
from database.connection import session_scope
from database.models import User
from services.course_service import enroll, ensure_default_catalog, list_courses

KEY = "bff-only-synthetic-secret-key-for-tests-12345"
PASSWORD = "Passw0rd!xyz"


def _headers(session: str | None = None) -> dict[str, str]:
    headers = {"X-Preluma-BFF-Key": KEY}
    if session:
        headers["X-Preluma-Session"] = session
    return headers


def test_api_fails_closed_without_bff_configuration(monkeypatch):
    with TestClient(app) as client:
        response = client.get("/v1/status")
        assert response.status_code == 503
        monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
        assert client.get("/v1/status").status_code == 401
        assert client.get("/v1/status", headers={"X-Preluma-BFF-Key": "wrong"}).status_code == 401
        response = client.get("/v1/status", headers=_headers())
        assert response.json() == {"status": "ok", "api_version": "v1"}
        assert response.headers["cache-control"] == "no-store"


def test_versioned_catalog_is_read_only_and_typed(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    ensure_default_catalog()
    expected = list_courses()
    with TestClient(app) as client:
        response = client.get("/v1/catalog/courses", headers=_headers())
        assert response.status_code == 200
        courses = response.json()["courses"]
        assert len(courses) == len(expected)
        assert set(courses[0]) == {"id", "slug", "title", "description", "level", "lesson_count",
                                   "enrolled", "completed_lessons", "percent"}
        assert client.post("/v1/catalog/courses", headers=_headers()).status_code == 405
        assert client.get("/v1/me", headers=_headers()).status_code == 401
        schema = app.openapi()
        assert schema["paths"]["/v1/catalog/courses"]["get"]["responses"]["200"]["content"][
            "application/json"]["schema"]["$ref"].endswith("CourseListResponse")
        for path, operations in schema["paths"].items():
            assert set(operations) == ({"post"} if path.startswith("/v1/auth/") else {"get"})


def test_private_endpoints_require_revocable_session_and_refresh_role(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    ensure_default_catalog()
    student = create_user("api-student", PASSWORD, "Student")
    other = create_user("api-other", PASSWORD, "Other")
    first_course = list_courses()[0].id
    enroll(student.id, first_course)
    token = create_session_token(student.id)
    other_token = create_session_token(other.id)
    with TestClient(app) as client:
        mine = client.get("/v1/me/courses", headers=_headers(token))
        theirs = client.get("/v1/me/courses", headers=_headers(other_token))
        assert mine.status_code == theirs.status_code == 200
        assert any(course["enrolled"] for course in mine.json()["courses"])
        assert not any(course["enrolled"] for course in theirs.json()["courses"])
        assert "password_hash" not in client.get("/v1/me", headers=_headers(token)).text
        with session_scope() as session:
            session.get(User, student.id).role = "teacher"
        assert client.get("/v1/me", headers=_headers(token)).json()["role"] == "teacher"
        revoke_session_token(token)
        assert client.get("/v1/me", headers=_headers(token)).status_code == 401
        with session_scope() as session:
            session.get(User, other.id).is_active = False
        assert client.get("/v1/me/courses", headers=_headers(other_token)).status_code == 401
