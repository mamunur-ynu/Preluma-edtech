"""Private read-only learning contract and course-isolation regression tests."""

from fastapi.testclient import TestClient

from api.app import app
from auth import create_user
from auth.sessions import create_session_token, revoke_session_token
from database.connection import session_scope
from database.models import Course, Lesson, User
from database.models import LearningEvent
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.learning_service import record_quiz_attempt
from sqlalchemy import select

KEY = "synthetic-recommendation-bff-key-for-tests-12345"


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {"X-Preluma-BFF-Key": KEY}
    if token:
        headers["X-Preluma-Session"] = token
    return headers


def test_recommendation_contract_denies_other_course_and_revoked_session(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    learner = create_user("contract-learner", "Passw0rd!xyz", "Learner")
    other = create_user("contract-other", "Passw0rd!xyz", "Other")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="recommendation-a", title="Statistics A"))
        hidden = CourseRepository(session).add(Course(slug="recommendation-b", title="Statistics B"))
        for row in (course, hidden):
            LessonRepository(session).add(Lesson(course_id=row.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        EnrollmentRepository(session).enroll(other.id, hidden.id)
        own_id, hidden_id = course.id, hidden.id
    token = create_session_token(learner.id)
    other_token = create_session_token(other.id)
    path = f"/v1/me/courses/{own_id}/recommendation"
    with TestClient(app) as client:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=_headers()).status_code == 401
        assert client.get(path, headers={"X-Preluma-BFF-Key": "wrong", "X-Preluma-Session": token}).status_code == 401
        assert client.get(path, headers=_headers(other_token)).status_code == 403
        assert client.get(f"/v1/me/courses/{hidden_id}/recommendation", headers=_headers(token)).status_code == 403
        own = client.get(path, headers=_headers(token))
        assert own.status_code == 200
        assert own.json() == {
            "course_id": own_id, "lesson_id": own.json()["lesson_id"], "rule_id": "cold_start",
            "rule_version": 1, "topic": "statistics", "title": "Start Stats",
            "reason": "No attributed quiz evidence for Stats in Statistics A yet.",
            "score": None, "attempts": 0, "evidence_event_ids": [],
        }
        assert own.headers["cache-control"] == "no-store"
        assert client.post(path, headers=_headers(token)).status_code == 405
        schema = app.openapi()
        assert schema["paths"]["/v1/me/courses/{course_id}/recommendation"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("CourseRecommendationResponse")
        revoke_session_token(token)
        assert client.get(path, headers=_headers(token)).status_code == 401


def test_recommendation_contract_minimizes_evidence_and_denies_deactivated(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    learner = create_user("contract-private", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="private-a", title="Private A"))
        LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        course_id = course.id
    record_quiz_attempt(learner.id, "statistics", 1, 2, course_id=course_id, details=[
        {"correct": False, "concept": "mean", "q": "SECRET QUESTION", "chosen": "SECRET ANSWER"},
    ])
    token = create_session_token(learner.id)
    path = f"/v1/me/courses/{course_id}/recommendation"
    with TestClient(app) as client:
        response = client.get(path, headers=_headers(token))
        assert response.status_code == 200
        assert response.json()["rule_id"] == "provisional_practice"
        assert len(response.json()["evidence_event_ids"]) == 1
        assert "SECRET" not in response.text
        with session_scope() as session:
            session.get(User, learner.id).is_active = False
        assert client.get(path, headers=_headers(token)).status_code == 401


def test_corrupt_evidence_fails_closed_without_payload_leak(monkeypatch):
    monkeypatch.setenv("PRELUMA_BFF_SHARED_KEY", KEY)
    learner = create_user("corrupt-private", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="corrupt-a", title="Corrupt A"))
        LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        course_id = course.id
    record_quiz_attempt(learner.id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        session.scalar(select(LearningEvent)).payload_json = "{PRIVATE CORRUPT PAYLOAD"
    token = create_session_token(learner.id)
    with TestClient(app) as client:
        response = client.get(f"/v1/me/courses/{course_id}/recommendation", headers=_headers(token))
        assert response.status_code == 503
        assert response.json() == {"detail": "Recommendation temporarily unavailable."}
        assert "PRIVATE" not in response.text
