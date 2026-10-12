"""Teacher analytics must never reveal another course's students or mistakes."""

import pytest

from auth import create_user
from database.connection import session_scope
from database.models import Course
from database.repository import CourseRepository, EnrollmentRepository, UserRepository
from services import analytics_service, course_service, learning_service

PASSWORD = "Passw0rd!xyz"


def _enroll(user_id: int, course_id: int) -> None:
    with session_scope() as session:
        EnrollmentRepository(session).enroll(user_id, course_id)


def _mistake(user_id: int, concept: str) -> None:
    learning_service.record_quiz_attempt(
        user_id, "statistics", 0, 1,
        details=[{"correct": False, "concept": concept, "q": "Question", "chosen": "A", "answer": "B"}],
    )


def test_teacher_dashboard_scopes_courses_roster_mistakes_and_drilldown():
    teacher_a = create_user("teacher-a", PASSWORD, "Teacher A", "teacher")
    teacher_b = create_user("teacher-b", PASSWORD, "Teacher B", "teacher")
    student_a = create_user("student-a", PASSWORD, "Student A")
    student_b = create_user("student-b", PASSWORD, "Student B")
    with session_scope() as session:
        repo = CourseRepository(session)
        course_a = repo.add(Course(slug="course-a", title="Course A", owner_id=teacher_a.id))
        course_b = repo.add(Course(slug="course-b", title="Course B", owner_id=teacher_b.id))
        course_a_id, course_b_id = course_a.id, course_b.id
    _enroll(student_a.id, course_a_id)
    _enroll(student_b.id, course_b_id)
    _mistake(student_a.id, "allowed-concept")
    _mistake(student_b.id, "secret-concept")

    assert [course.id for course in course_service.list_teacher_courses(teacher_a.id)] == [course_a_id]
    own = analytics_service.class_overview(teacher_a.id)
    assert {row.user_id for row in own.student_rows} == {student_a.id}
    assert {item["concept"] for item in own.top_mistakes} == {"allowed-concept"}
    assert analytics_service.class_overview(teacher_a.id, course_a_id).students == 1
    assert analytics_service.student_detail(teacher_a.id, student_a.id)["topics"]
    with pytest.raises(PermissionError):
        analytics_service.class_overview(teacher_a.id, course_b_id)
    with pytest.raises(PermissionError):
        analytics_service.student_detail(teacher_a.id, student_b.id)
    with pytest.raises(PermissionError):
        analytics_service.student_detail(teacher_a.id, student_a.id, course_b_id)
    assert analytics_service.class_overview(teacher_b.id).students == 1


def test_teacher_analytics_rejects_students_and_disabled_teachers():
    student = create_user("student", PASSWORD, "Student")
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    for actor_id in (student.id,):
        with pytest.raises(PermissionError):
            analytics_service.class_overview(actor_id)
        with pytest.raises(PermissionError):
            analytics_service.student_detail(actor_id, student.id)
        with pytest.raises(PermissionError):
            course_service.list_teacher_courses(actor_id)
    with session_scope() as session:
        UserRepository(session).get(teacher.id).is_active = False
    with pytest.raises(PermissionError):
        analytics_service.class_overview(teacher.id)
    with pytest.raises(PermissionError):
        course_service.list_teacher_courses(teacher.id)


def test_shared_default_course_is_accessible_to_teachers_and_admin_sees_all():
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    admin = create_user("admin", PASSWORD, "Admin", "admin")
    student = create_user("student", PASSWORD, "Student")
    with session_scope() as session:
        shared = CourseRepository(session).add(Course(slug="shared", title="Shared", owner_id=None))
        shared_id = shared.id
    _enroll(student.id, shared_id)
    assert analytics_service.class_overview(teacher.id, shared_id).students == 1
    assert analytics_service.class_overview(admin.id).students == 1
    assert analytics_service.student_detail(admin.id, student.id)["topics"] == []
