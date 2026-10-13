"""Synthetic deletion behavior; not a production erasure workflow."""

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from auth import create_user
from database.connection import session_scope
from database.models import (
    Course, CourseMastery, KnowledgeDocument, LearningEvent, LearningOutbox,
    Lesson, QuizAttempt, User,
)
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository
from services.learning_service import record_quiz_attempt


def test_synthetic_learner_delete_cascades_learning_evidence():
    learner = create_user("erase-learner", "Passw0rd!xyz", "Learner")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="erase-course", title="Erase course"))
        LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        EnrollmentRepository(session).enroll(learner.id, course.id)
        course_id = course.id
    record_quiz_attempt(learner.id, "statistics", 1, 2, course_id=course_id)
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 1
        assert session.scalar(select(func.count()).select_from(LearningOutbox)) == 1
        assert session.scalar(select(func.count()).select_from(CourseMastery)) == 1
        session.execute(delete(User).where(User.id == learner.id))
    with session_scope() as session:
        for model in (User, QuizAttempt, LearningEvent, LearningOutbox, CourseMastery):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.get(Course, course_id) is not None


def test_referenced_uploaded_document_blocks_unplanned_account_deletion():
    teacher = create_user("erase-teacher", "Passw0rd!xyz", "Teacher", role="teacher")
    with session_scope() as session:
        session.add(KnowledgeDocument(title="Private source", uploaded_by=teacher.id,
                                      visibility="private", source_ciphertext=b"synthetic"))
    with pytest.raises(IntegrityError):
        with session_scope() as session:
            session.execute(delete(User).where(User.id == teacher.id))
    with session_scope() as session:
        assert session.get(User, teacher.id) is not None
        assert session.scalar(select(KnowledgeDocument)).uploaded_by == teacher.id
