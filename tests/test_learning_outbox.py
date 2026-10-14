"""Synthetic, single-process outbox replay tests; no production data or worker."""

from datetime import datetime

import pytest
from sqlalchemy import select

from auth import create_user, end_session, start_session
from database.connection import session_scope
from database.models import Course, CourseMastery, LearningEvent, LearningOutbox, Lesson, User
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.learning_outbox import process_next_learning_event, quarantine_invalid_learning_event
from services.learning_service import record_quiz_attempt


def _course():
    user = create_user("outbox_learner", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="outbox", title="Outbox"))
        LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(user.id, course.id)
        return user.id, course.id


def _admin_session():
    admin = create_user("outbox_admin", "Passw0rd!xyz", "Outbox Admin", "admin")
    return admin.id, start_session(admin)


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


def test_explicit_quarantine_preserves_bad_evidence_and_unblocks_other_course():
    user_id, course_id = _course()
    admin_id, admin_token = _admin_session()
    record_quiz_attempt(user_id, "statistics", 5, 10, course_id=course_id)
    with session_scope() as session:
        bad = session.scalar(select(LearningEvent))
        bad_id = bad.id
        bad.payload_json = "{invalid"
    with pytest.raises(ValueError):
        process_next_learning_event()
    assert quarantine_invalid_learning_event(bad_id, admin_token)
    assert quarantine_invalid_learning_event(bad_id, admin_token)
    with session_scope() as session:
        marker = session.get(LearningOutbox, bad_id)
        assert marker.delivered_at is None
        assert marker.quarantined_at is not None
        assert marker.quarantine_reason == "invalid_evidence"
        assert marker.quarantined_by_user_id == admin_id
        assert session.get(LearningEvent, bad_id).payload_json == "{invalid"

        other = CourseRepository(session).add(Course(slug="other", title="Other"))
        LessonRepository(session).add(Lesson(course_id=other.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(user_id, other.id)
        other_id = other.id
    record_quiz_attempt(user_id, "statistics", 8, 10, course_id=other_id)
    assert process_next_learning_event() is not None
    assert process_next_learning_event() is None
    with session_scope() as session:
        assert session.get(LearningOutbox, bad_id).delivered_at is None
        assert session.scalar(select(CourseMastery).where(CourseMastery.course_id == other_id)) is not None


def test_valid_event_cannot_be_quarantined():
    user_id, course_id = _course()
    _, admin_token = _admin_session()
    record_quiz_attempt(user_id, "statistics", 5, 10, course_id=course_id)
    with session_scope() as session:
        event_id = session.scalar(select(LearningEvent)).id
    assert not quarantine_invalid_learning_event(event_id, admin_token)
    assert not quarantine_invalid_learning_event("missing", admin_token)
    with session_scope() as session:
        marker = session.get(LearningOutbox, event_id)
        assert marker.quarantined_at is None
        assert marker.delivered_at is None
    assert process_next_learning_event() == event_id
    assert not quarantine_invalid_learning_event(event_id, admin_token)


def test_course_less_bad_evidence_is_not_silently_acknowledged():
    user_id, _ = _course()
    _, admin_token = _admin_session()
    with session_scope() as session:
        other = CourseRepository(session).add(Course(slug="ambiguous", title="Ambiguous"))
        LessonRepository(session).add(Lesson(course_id=other.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(user_id, other.id)
    record_quiz_attempt(user_id, "statistics", 1, 1)
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        assert event.course_id is None
        event_id = event.id
        event.payload_json = "{invalid"
    with pytest.raises(ValueError):
        process_next_learning_event()
    assert quarantine_invalid_learning_event(event_id, admin_token)
    with session_scope() as session:
        marker = session.get(LearningOutbox, event_id)
        assert marker.delivered_at is None
        assert marker.quarantine_reason == "invalid_evidence"


def test_unsupported_event_is_quarantined_without_acknowledgement():
    user_id, course_id = _course()
    _, admin_token = _admin_session()
    record_quiz_attempt(user_id, "statistics", 1, 1, course_id=course_id)
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        event_id = event.id
        event.schema_version = 99
    with pytest.raises(ValueError):
        process_next_learning_event()
    assert quarantine_invalid_learning_event(event_id, admin_token)
    with session_scope() as session:
        marker = session.get(LearningOutbox, event_id)
        assert marker.delivered_at is None
        assert marker.quarantine_reason == "unsupported_schema"


def test_quarantine_denies_non_admin_revoked_and_deactivated_sessions():
    user_id, course_id = _course()
    _, admin_token = _admin_session()
    teacher = create_user("outbox_teacher", "Passw0rd!xyz", "Teacher", "teacher")
    record_quiz_attempt(user_id, "statistics", 1, 1, course_id=course_id)
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        event_id = event.id
        event.payload_json = "{invalid"
    for token in ("", "invalid", start_session(teacher)):
        with pytest.raises(PermissionError):
            quarantine_invalid_learning_event(event_id, token)
    end_session(admin_token)
    with pytest.raises(PermissionError):
        quarantine_invalid_learning_event(event_id, admin_token)
    active_admin = create_user("active_admin", "Passw0rd!xyz", "Active Admin", "admin")
    inactive_token = start_session(active_admin)
    with session_scope() as session:
        session.get(User, active_admin.id).is_active = False
    with pytest.raises(PermissionError):
        quarantine_invalid_learning_event(event_id, inactive_token)
    demoted_admin = create_user("demoted_admin", "Passw0rd!xyz", "Demoted Admin", "admin")
    demoted_token = start_session(demoted_admin)
    with session_scope() as session:
        session.get(User, demoted_admin.id).role = "teacher"
    with pytest.raises(PermissionError):
        quarantine_invalid_learning_event(event_id, demoted_token)
    with session_scope() as session:
        marker = session.get(LearningOutbox, event_id)
        assert marker.quarantined_at is None
        assert marker.quarantined_by_user_id is None


def test_configured_admin_session_can_quarantine(monkeypatch):
    user_id, course_id = _course()
    configured = create_user("configured_admin", "Passw0rd!xyz", "Configured Admin")
    token = start_session(configured)
    monkeypatch.setenv("PRELUMA_ADMIN_USERS", configured.username)
    record_quiz_attempt(user_id, "statistics", 1, 1, course_id=course_id)
    with session_scope() as session:
        event = session.scalar(select(LearningEvent))
        event_id = event.id
        event.payload_json = "{invalid"
    assert quarantine_invalid_learning_event(event_id, token)
    with session_scope() as session:
        assert session.get(LearningOutbox, event_id).quarantined_by_user_id == configured.id
