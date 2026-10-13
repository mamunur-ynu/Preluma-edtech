"""Shadow rule engine is deterministic, evidence-linked and enrollment scoped."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from auth import create_user
from database.connection import session_scope
from database.models import Course, LearningEvent, Lesson
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository, UserRepository
from services.course_recommendations import get_course_recommendation
from services.learning_service import record_quiz_attempt


def _course():
    learner = create_user("learner", "Passw0rd!xyz", "Learner")
    other = create_user("other", "Passw0rd!xyz", "Other")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="stats", title="Statistics Course"))
        LessonRepository(session).add(Lesson(
            course_id=course.id, topic_key="statistics", title="Statistics", order_index=1,
        ))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        return learner.id, other.id, course.id


def test_cold_start_provisional_practice_and_course_scope():
    user_id, other_id, course_id = _course()
    now = datetime(2026, 10, 13)
    first = get_course_recommendation(user_id, course_id, now=now)
    assert (first.rule_id, first.evidence_event_ids, first.attempts) == ("cold_start", (), 0)
    record_quiz_attempt(user_id, "statistics", 6, 10, course_id=course_id, when=now - timedelta(days=2))
    provisional = get_course_recommendation(user_id, course_id, now=now)
    assert (provisional.rule_id, provisional.score, provisional.attempts) == (
        "provisional_practice", 60.0, 1,
    )
    record_quiz_attempt(user_id, "statistics", 2, 10, course_id=course_id, when=now - timedelta(days=1))
    practice = get_course_recommendation(user_id, course_id, now=now)
    assert (practice.rule_id, practice.score, practice.attempts) == ("practice", 33.3, 2)
    assert "33.3%" in practice.reason and "Statistics Course" in practice.reason
    with session_scope() as session:
        ids = tuple(session.scalars(select(LearningEvent.id).order_by(LearningEvent.occurred_at)).all())
    assert practice.evidence_event_ids == ids
    with pytest.raises(PermissionError):
        get_course_recommendation(other_id, course_id, now=now)
    with session_scope() as session:
        UserRepository(session).get(user_id).is_active = False
    with pytest.raises(PermissionError):
        get_course_recommendation(user_id, course_id, now=now)


def test_stale_review_then_next_lesson_without_cross_course_guessing():
    user_id, _, course_id = _course()
    now = datetime(2026, 10, 13)
    record_quiz_attempt(user_id, "statistics", 7, 10, course_id=course_id, when=now - timedelta(days=25))
    record_quiz_attempt(user_id, "statistics", 8, 10, course_id=course_id, when=now - timedelta(days=20))
    review = get_course_recommendation(user_id, course_id, now=now)
    assert (review.rule_id, review.score) == ("review", 76.7)
    assert "2026-09-23" in review.reason
    with session_scope() as session:
        LessonRepository(session).add(Lesson(
            course_id=course_id, topic_key="python programming", title="Python", order_index=2,
        ))
    record_quiz_attempt(user_id, "statistics", 10, 10, course_id=course_id, when=now - timedelta(days=1))
    next_step = get_course_recommendation(user_id, course_id, now=now)
    assert (next_step.rule_id, next_step.topic) == ("cold_start", "python programming")
    assert next_step.evidence_event_ids == ()


def test_course_ready_only_after_two_attributed_high_scores():
    user_id, _, course_id = _course()
    now = datetime(2026, 10, 13)
    record_quiz_attempt(user_id, "statistics", 10, 10, course_id=course_id, when=now - timedelta(days=2))
    assert get_course_recommendation(user_id, course_id, now=now).rule_id == "provisional_practice"
    record_quiz_attempt(user_id, "statistics", 9, 10, course_id=course_id, when=now - timedelta(days=1))
    result = get_course_recommendation(user_id, course_id, now=now)
    assert (result.rule_id, result.lesson_id) == ("course_ready", None)
