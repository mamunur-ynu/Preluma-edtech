"""Relational schema + repository pattern + learning-service persistence."""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from auth import create_user
from database.connection import session_scope
from database.models import Course, Lesson, QuizAttempt, User
from database.repository import (
    AchievementRepository, CourseRepository, EnrollmentRepository, LessonRepository, ProgressRepository,
    QuizAttemptRepository, SkillProfileRepository, UserRepository,
)
from services import course_service, learning_service
from services._common import now_utc

PW = "Passw0rd!xyz"


def test_all_required_tables_exist():
    from database.models import Base

    required = {"users", "courses", "lessons", "enrollments", "progress", "quiz_attempts", "skill_profiles",
                "ai_conversation_history", "recommendations", "achievements"}
    assert required <= set(Base.metadata.tables)


def test_usernames_are_unique():
    with pytest.raises(IntegrityError):
        with session_scope() as s:
            repo = UserRepository(s)
            repo.add(User(username="dup", password_hash="x", role="student", full_name="A"))
            repo.add(User(username="dup", password_hash="x", role="student", full_name="B"))


def test_session_scope_rolls_back_on_error():
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            UserRepository(s).add(User(username="ghost", password_hash="x", role="student", full_name="G"))
            raise RuntimeError("boom")
    with session_scope() as s:
        assert UserRepository(s).get_by_username("ghost") is None


def test_enrollment_is_idempotent_and_progress_upserts():
    user = create_user("eve", PW, "Eve")
    with session_scope() as s:
        course = CourseRepository(s).add(Course(slug="c1", title="C1", description="d", level="Beginner"))
        lesson = LessonRepository(s).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats", order_index=1))
        cid, lid = course.id, lesson.id
    with session_scope() as s:
        repo = EnrollmentRepository(s)
        assert repo.enroll(user.id, cid)[1] is True
        assert repo.enroll(user.id, cid)[1] is False
        assert repo.course_ids_for_user(user.id) == [cid]
    with session_scope() as s:
        progress = ProgressRepository(s)
        progress.upsert(user.id, lid, status="in_progress", percent=40, add_seconds=30)
        progress.upsert(user.id, lid, status="completed", percent=90, add_seconds=30)
        row = progress.get(user.id, lid)
        assert (row.status, row.percent, row.time_spent_seconds) == ("completed", 100, 60)   # completing a lesson snaps it to 100%


def test_quiz_attempt_updates_skill_profile_and_achievements():
    user = create_user("finn", PW, "Finn")
    outcome = learning_service.record_quiz_attempt(user.id, "Python Programming", 4, 5, duration_seconds=100)
    assert outcome.topic == "python programming" and outcome.percentage == 80
    assert "first_quiz" in {code for code in _codes(user.id)}
    with session_scope() as s:
        row = SkillProfileRepository(s).get(user.id, "python programming")
        assert row.attempts == 1 and 50 < row.mastery < 100
        assert QuizAttemptRepository(s).count_for_user(user.id) == 1


def _codes(user_id):
    with session_scope() as s:
        return AchievementRepository(s).codes_for_user(user_id)


def test_service_returns_plain_objects_not_orm_rows():
    user = create_user("gina", PW, "Gina")
    learning_service.record_quiz_attempt(user.id, "statistics", 3, 5)
    dashboard = learning_service.get_dashboard(user.id)         # usable after the session closed
    assert dashboard.topics[0].title == "Statistics"
    assert not hasattr(dashboard, "_sa_instance_state")


def test_default_catalog_is_idempotent_and_ordered_by_prerequisites():
    assert course_service.ensure_default_catalog() == len(course_service.DEFAULT_COURSES)
    assert course_service.ensure_default_catalog() == 0
    course = next(c for c in course_service.list_courses() if c.slug == "ai-and-machine-learning")
    detail = course_service.get_course(course.id)
    order = [lesson.topic_key for lesson in detail.lessons]
    assert order.index("machine learning") < order.index("neural network") < order.index("convolutional neural network")


def test_completing_a_quiz_completes_the_matching_lesson():
    course_service.ensure_default_catalog()
    user = create_user("hana", PW, "Hana")
    course = next(c for c in course_service.list_courses() if c.slug == "programming-foundations")
    course_service.enroll(user.id, course.id)
    outcome = learning_service.record_quiz_attempt(user.id, "python programming", 5, 5)
    assert outcome.lessons_completed >= 1
    refreshed = course_service.get_course(course.id, user.id)
    assert refreshed.completed_lessons >= 1 and refreshed.percent > 0


def test_only_teachers_create_courses():
    student = create_user("ivan", PW, "Ivan")
    teacher = create_user("jane", PW, "Jane", "teacher")
    with pytest.raises(PermissionError):
        course_service.create_course(student.id, "My Course", "d", ["statistics"])
    course_id = course_service.create_course(teacher.id, "Stats 101", "d", ["statistics"])
    assert course_service.get_course(course_id).lesson_count == 1


def test_recent_attempts_query_respects_window():
    user = create_user("kyle", PW, "Kyle")
    old = now_utc() - timedelta(days=200)
    learning_service.record_quiz_attempt(user.id, "statistics", 3, 5, when=old)
    learning_service.record_quiz_attempt(user.id, "statistics", 4, 5)
    with session_scope() as s:
        assert len(QuizAttemptRepository(s).all_recent(30)) == 1
        assert s.query(QuizAttempt).count() == 2
