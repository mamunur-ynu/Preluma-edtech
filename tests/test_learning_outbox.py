"""Synthetic, single-process outbox replay tests; no production data or worker."""

from datetime import datetime

import pytest
from sqlalchemy import select

from auth import create_user
from database.connection import session_scope
from database.models import Course, CourseMastery, LearningEvent, LearningOutbox, Lesson
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.learning_outbox import process_next_learning_event
from services.learning_service import record_quiz_attempt


def _course():
    user = create_user("outbox_learner", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="outbox", title="Outbox"))
        LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(user.id, course.id)
        return user.id, course.id


def test_replay_is_idempotent_and_course_scoped():
    user_id, course_id = _course()
    record_quiz_attempt(user_id, "statistics", 2, 10, course_id=course_id, when=datetime(2026, 1, 2))
    record_quiz_attempt(user_id, "statistics", 8, 10, course_id=course_id, when=datetime(2026, 1, 1))
    with session_scope() as session:
        before = [(row.topic, row.mastery, row.attempts, row.last_event_id) for row in
                  session.scalars(select(CourseMastery)).all()]
        assert len(before) == 1
    assert process_next_learning_event() is not None
    assert process_next_learning_event() is not None
    assert process_next_learning_event() is None
    with session_scope() as session:
        after = [(row.topic, row.mastery, row.attempts, row.last_event_id) for row in
                 session.scalars(select(CourseMastery)).all()]
        assert after == before
        assert all(row.delivered_at is not None for row in session.scalars(select(LearningOutbox)))


def test_ambiguous_evidence_is_acknowledged_without_course_projection():
    user_id, _ = _course()
    with session_scope() as session:
        other = CourseRepository(session).add(Course(slug="other", title="Other"))
        LessonRepository(session).add(Lesson(course_id=other.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(user_id, other.id)
    record_quiz_attempt(user_id, "statistics", 1, 1)
    with session_scope() as session:
        assert session.scalar(select(LearningEvent)).course_id is None
    assert process_next_learning_event() is not None
    with session_scope() as session:
        assert session.scalars(select(CourseMastery)).all() == []
        assert session.scalar(select(LearningOutbox)).delivered_at is not None


def test_failed_replay_does_not_acknowledge_or_change_projection():
    user_id, course_id = _course()
    record_quiz_attempt(user_id, "statistics", 5, 10, course_id=course_id)
    with session_scope() as session:
        before = session.scalar(select(CourseMastery)).mastery
        session.scalar(select(LearningEvent)).payload_json = "{invalid"
    with pytest.raises(ValueError):
        process_next_learning_event()
    with session_scope() as session:
        assert session.scalar(select(CourseMastery)).mastery == before
        assert session.scalar(select(LearningOutbox)).delivered_at is None
