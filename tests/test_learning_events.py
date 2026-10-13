"""Synthetic evidence tests: no student production data or external calls."""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from auth import create_user
from database.connection import session_scope
from database.models import Course, CourseMastery, LearningEvent, LearningOutbox, Lesson, QuizAttempt
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.learning_events import append_quiz_event, rebuild_course_mastery
from services.learning_service import record_quiz_attempt
from services.course_recommendations import get_course_recommendation


def _two_courses():
    user = create_user("learner", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        courses = [CourseRepository(session).add(Course(slug=slug, title=slug)) for slug in ("a", "b")]
        for course in courses:
            LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
            EnrollmentRepository(session).enroll(user.id, course.id)
        return user.id, courses[0].id, courses[1].id


def test_course_evidence_isolated_and_private():
    user_id, a, b = _two_courses()
    now = datetime(2026, 1, 1)
    record_quiz_attempt(user_id, "statistics", 2, 2, when=now, details=[
        {"correct": True, "q": "SECRET QUESTION", "chosen": "SECRET ANSWER"},
    ])  # ambiguous, never attributed to either course
    record_quiz_attempt(user_id, "statistics", 2, 10, course_id=a, when=now + timedelta(days=1))
    record_quiz_attempt(user_id, "statistics", 8, 10, course_id=b, when=now + timedelta(days=2))
    record_quiz_attempt(user_id, "statistics", 10, 10, course_id=a, when=now + timedelta(days=3))
    with session_scope() as session:
        events = session.scalars(select(LearningEvent).order_by(LearningEvent.occurred_at)).all()
        assert [event.course_id for event in events] == [None, a, b, a]
        assert all("SECRET" not in event.payload_json for event in events)
        rows = session.scalars(select(CourseMastery).order_by(CourseMastery.course_id)).all()
        assert [(row.course_id, row.mastery, row.attempts) for row in rows] == [
            (a, 73.3, 2), (b, 80.0, 1),
        ]
        assert session.scalar(select(func.count()).select_from(LearningOutbox)) == 4
        assert all(row.concept == "" for row in rows)


def test_idempotent_append_and_deterministic_replay():
    user_id, a, _ = _two_courses()
    now = datetime(2026, 1, 1)
    first = record_quiz_attempt(user_id, "statistics", 4, 10, course_id=a, when=now + timedelta(days=2))
    second = record_quiz_attempt(user_id, "statistics", 10, 10, course_id=a, when=now)
    with session_scope() as session:
        from database.models import QuizAttempt

        attempt = session.get(QuizAttempt, first.attempt_id)
        event = append_quiz_event(session, attempt)
        assert event.source_id == str(attempt.id)
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 2
        before = session.scalar(select(CourseMastery).where(CourseMastery.course_id == a))
        assert (before.mastery, before.last_event_id) == (60.0, event.id)
        rebuilt = rebuild_course_mastery(session, user_id, a)
        assert len(rebuilt) == 1
        assert (rebuilt[0].mastery, rebuilt[0].last_event_id) == (60.0, event.id)
        assert session.scalar(select(func.count()).select_from(CourseMastery)) == 1
    assert first.attempt_id != second.attempt_id


def test_concept_evidence_is_aggregated_without_answers_and_course_scoped():
    user_id, a, b = _two_courses()
    details_a = [
        {"correct": True, "concept": "mean", "q": "PRIVATE QUESTION", "chosen": "PRIVATE ANSWER"},
        {"correct": False, "concept": "mean", "q": "OTHER PRIVATE QUESTION", "chosen": "OTHER ANSWER"},
        {"correct": True, "concept": "median", "q": "MORE PRIVATE QUESTION"},
    ]
    record_quiz_attempt(user_id, "statistics", 2, 3, course_id=a, details=details_a)
    record_quiz_attempt(user_id, "statistics", 0, 1, course_id=b, details=[
        {"correct": False, "concept": "mean", "q": "COURSE B SECRET"},
    ])
    with session_scope() as session:
        events = session.scalars(select(LearningEvent)).all()
        assert all("PRIVATE" not in event.payload_json and "SECRET" not in event.payload_json for event in events)
        rows = session.scalars(select(CourseMastery)).all()
        values = {(row.course_id, row.concept): row.mastery for row in rows}
        assert values[(a, "mean")] == 50.0
        assert values[(a, "median")] == 100.0
        assert values[(b, "mean")] == 0.0
        assert (b, "median") not in values
        first = next(event for event in events if event.course_id == a)
        assert json.loads(first.payload_json)["concepts"] == [
            {"concept": "mean", "score": 1, "total": 2},
            {"concept": "median", "score": 1, "total": 1},
        ]


def test_event_and_outbox_are_transactional():
    user_id, a, _ = _two_courses()
    with pytest.raises(RuntimeError):
        with session_scope() as session:
            attempt = QuizAttempt(
                user_id=user_id, course_id=a, topic="statistics", score=1, total=2,
                percentage=50.0, created_at=datetime(2026, 1, 1),
            )
            session.add(attempt)
            append_quiz_event(session, attempt)
            raise RuntimeError("rollback")
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(QuizAttempt)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningOutbox)) == 0

    record_quiz_attempt(user_id, "statistics", 1, 2, course_id=a)
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        assert json.loads(event.payload_json)["score"] == 1
        session.add(LearningEvent(
            id="duplicate", schema_version=1, event_type="quiz.completed", user_id=user_id,
            course_id=a, source_type="quiz_attempt", source_id="duplicate",
            producer=event.producer, idempotency_key=event.idempotency_key,
            occurred_at=event.occurred_at, payload_json=event.payload_json,
        ))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


@pytest.mark.parametrize("corruption", ["course", "score", "source", "concept"])
def test_replay_and_shadow_read_fail_closed_on_evidence_drift(corruption):
    user_id, a, b = _two_courses()
    record_quiz_attempt(user_id, "statistics", 1, 2, course_id=a, details=[
        {"correct": True, "concept": "mean"},
    ])
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        if corruption == "course":
            event.course_id = b
        elif corruption == "score":
            payload = json.loads(event.payload_json)
            payload["score"] = 2
            event.payload_json = json.dumps(payload)
        elif corruption == "source":
            event.source_id = "999999"
        else:
            payload = json.loads(event.payload_json)
            payload["concepts"].append(payload["concepts"][0])
            event.payload_json = json.dumps(payload)
    target = b if corruption == "course" else a
    with pytest.raises(ValueError), session_scope() as session:
        rebuild_course_mastery(session, user_id, target)
    with pytest.raises(ValueError):
        get_course_recommendation(user_id, target)
    if corruption == "course":
        with pytest.raises(ValueError):
            get_course_recommendation(user_id, a)
    with session_scope() as session:
        rows = session.scalars(select(CourseMastery)).all()
        assert len(rows) == 2  # topic and concept from the original valid attempt
        assert all(row.course_id == a for row in rows)
