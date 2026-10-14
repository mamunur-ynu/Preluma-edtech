"""Synthetic append-only correction tests; no public mutation or live data."""

import json

import pytest
from sqlalchemy import select

from auth import create_user, end_session, start_session
from database.connection import session_scope
from database.models import Course, CourseMastery, LearningEvent, LearningOutbox, Lesson, QuizAttempt, User
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.course_recommendations import get_course_recommendation
from services.learning_corrections import void_quiz_evidence
from services.learning_outbox import process_next_learning_event, quarantine_invalid_learning_event
from services.learning_service import record_quiz_attempt


def _setup():
    learner = create_user("correction_learner", "Passw0rd!xyz", "Learner")
    admin = create_user("correction_admin", "Passw0rd!xyz", "Admin", "admin")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="correctable", title="Correctable"))
        LessonRepository(session).add(Lesson(
            course_id=course.id, topic_key="statistics", title="Statistics",
        ))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        course_id = course.id
    return learner.id, course_id, admin.id, start_session(admin)


def test_void_is_append_only_course_scoped_idempotent_and_replayable():
    learner_id, course_id, admin_id, token = _setup()
    record_quiz_attempt(learner_id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        original = session.scalar(select(LearningEvent))
        original_id, original_payload = original.id, original.payload_json
        attempt_id = int(original.source_id)
    assert get_course_recommendation(learner_id, course_id).rule_id == "provisional_practice"
    correction_id = void_quiz_evidence(original_id, token, "assessment_error")
    assert void_quiz_evidence(original_id, token, "assessment_error") == correction_id
    with pytest.raises(ValueError, match="reason differs"):
        void_quiz_evidence(original_id, token, "duplicate_attempt")
    assert get_course_recommendation(learner_id, course_id).rule_id == "cold_start"
    with session_scope() as session:
        assert session.get(LearningEvent, original_id).payload_json == original_payload
        assert session.get(QuizAttempt, attempt_id) is not None
        correction = session.get(LearningEvent, correction_id)
        assert (correction.actor_user_id, correction.source_id, correction.course_id) == (
            admin_id, original_id, course_id,
        )
        assert json.loads(correction.payload_json)["reason_code"] == "assessment_error"
        assert session.get(LearningOutbox, correction_id).delivered_at is None
        assert session.scalars(select(CourseMastery)).all() == []
        assert len(session.scalars(select(LearningEvent)).all()) == 2
    assert process_next_learning_event() == original_id
    assert process_next_learning_event() == correction_id
    assert process_next_learning_event() is None
    assert get_course_recommendation(learner_id, course_id).rule_id == "cold_start"


def test_void_does_not_remove_same_topic_evidence_from_another_course():
    learner_id, course_id, _, token = _setup()
    with session_scope() as session:
        other = CourseRepository(session).add(Course(slug="parallel", title="Parallel"))
        LessonRepository(session).add(Lesson(
            course_id=other.id, topic_key="statistics", title="Parallel Statistics",
        ))
        EnrollmentRepository(session).enroll(learner_id, other.id)
        other_id = other.id
    record_quiz_attempt(learner_id, "statistics", 1, 2, course_id=course_id)
    record_quiz_attempt(learner_id, "statistics", 2, 2, course_id=other_id)
    with session_scope() as session:
        original_id = session.scalar(select(LearningEvent.id).where(LearningEvent.course_id == course_id))
    void_quiz_evidence(original_id, token, "teacher_review")
    assert get_course_recommendation(learner_id, course_id).rule_id == "cold_start"
    other_plan = get_course_recommendation(learner_id, other_id)
    assert (other_plan.rule_id, other_plan.score, other_plan.attempts) == (
        "provisional_practice", 100.0, 1,
    )


def test_void_requires_live_admin_and_retains_evidence_on_denial():
    learner_id, course_id, admin_id, token = _setup()
    teacher = create_user("correction_teacher", "Passw0rd!xyz", "Teacher", "teacher")
    teacher_token = start_session(teacher)
    record_quiz_attempt(learner_id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        original_id = session.scalar(select(LearningEvent.id))
    for denied in ("", "invalid", teacher_token):
        with pytest.raises(PermissionError):
            void_quiz_evidence(original_id, denied, "teacher_review")
    end_session(token)
    with pytest.raises(PermissionError):
        void_quiz_evidence(original_id, token, "teacher_review")
    admin = create_user("demoted_correction_admin", "Passw0rd!xyz", "Admin", "admin")
    demoted_token = start_session(admin)
    with session_scope() as session:
        session.get(User, admin.id).role = "teacher"
    with pytest.raises(PermissionError):
        void_quiz_evidence(original_id, demoted_token, "teacher_review")
    inactive_admin = create_user("inactive_correction_admin", "Passw0rd!xyz", "Admin", "admin")
    inactive_token = start_session(inactive_admin)
    with session_scope() as session:
        session.get(User, inactive_admin.id).is_active = False
    with pytest.raises(PermissionError):
        void_quiz_evidence(original_id, inactive_token, "teacher_review")
    with session_scope() as session:
        assert len(session.scalars(select(LearningEvent)).all()) == 1
        assert session.get(User, admin_id).is_active


def test_void_rejects_ambiguous_corrupt_and_quarantined_source():
    learner_id, course_id, _, token = _setup()
    with session_scope() as session:
        other = CourseRepository(session).add(Course(slug="other", title="Other"))
        LessonRepository(session).add(Lesson(
            course_id=other.id, topic_key="statistics", title="Other Statistics",
        ))
        EnrollmentRepository(session).enroll(learner_id, other.id)
    record_quiz_attempt(learner_id, "statistics", 1, 2)
    with session_scope() as session:
        ambiguous_id = session.scalar(select(LearningEvent.id))
    with pytest.raises(ValueError, match="Attributed"):
        void_quiz_evidence(ambiguous_id, token, "assessment_error")
    record_quiz_attempt(learner_id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        source = session.scalar(select(LearningEvent).where(LearningEvent.course_id == course_id))
        source_id = source.id
        source.payload_json = "{invalid"
    with pytest.raises(ValueError):
        void_quiz_evidence(source_id, token, "assessment_error")
    assert quarantine_invalid_learning_event(source_id, token)
    with pytest.raises(ValueError, match="Invalid quiz evidence"):
        void_quiz_evidence(source_id, token, "assessment_error")
    with session_scope() as session:
        assert len(session.scalars(select(LearningEvent)).all()) == 2


def test_tampered_correction_fails_closed():
    learner_id, course_id, _, token = _setup()
    record_quiz_attempt(learner_id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        original_id = session.scalar(select(LearningEvent.id))
    correction_id = void_quiz_evidence(original_id, token, "assessment_error")
    with session_scope() as session:
        session.get(LearningEvent, correction_id).payload_json = '{"reason_code":"bogus"}'
    with pytest.raises(ValueError):
        get_course_recommendation(learner_id, course_id)
    with pytest.raises(ValueError):
        process_next_learning_event()
    with session_scope() as session:
        assert session.get(LearningOutbox, correction_id).delivered_at is None
        assert session.get(LearningOutbox, original_id).delivered_at is None
