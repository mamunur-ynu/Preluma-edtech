"""Teacher analytics must never reveal another course's students or mistakes."""

import pytest

from auth import create_user
from database.connection import session_scope
from database.models import Course, Lesson
from database.repository import CourseRepository, EnrollmentRepository, LessonRepository, QuizAttemptRepository, UserRepository
from services import analytics_service, course_service, learning_service

PASSWORD = "Passw0rd!xyz"


def _enroll(user_id: int, course_id: int) -> None:
    with session_scope() as session:
        EnrollmentRepository(session).enroll(user_id, course_id)


def _mistake(user_id: int, concept: str, course_id: int) -> None:
    learning_service.record_quiz_attempt(
        user_id, "statistics", 0, 1, course_id=course_id,
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
        LessonRepository(session).add(Lesson(course_id=course_a.id, topic_key="statistics", title="Stats A"))
        LessonRepository(session).add(Lesson(course_id=course_b.id, topic_key="statistics", title="Stats B"))
        course_a_id, course_b_id = course_a.id, course_b.id
    _enroll(student_a.id, course_a_id)
    _enroll(student_b.id, course_b_id)
    _mistake(student_a.id, "allowed-concept", course_a_id)
    _mistake(student_b.id, "secret-concept", course_b_id)

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


def test_student_in_two_courses_has_course_specific_activity_only():
    teacher_a = create_user("teacher-a", PASSWORD, "Teacher A", "teacher")
    teacher_b = create_user("teacher-b", PASSWORD, "Teacher B", "teacher")
    student = create_user("student", PASSWORD, "Student")
    with session_scope() as session:
        repo = CourseRepository(session)
        a = repo.add(Course(slug="a", title="A", owner_id=teacher_a.id))
        b = repo.add(Course(slug="b", title="B", owner_id=teacher_b.id))
        for course in (a, b):
            LessonRepository(session).add(Lesson(course_id=course.id, topic_key="statistics", title="Stats"))
        a_id, b_id = a.id, b.id
    _enroll(student.id, a_id)
    _enroll(student.id, b_id)
    # An attempt without an explicit course stays unattributed rather than guessed.
    learning_service.record_quiz_attempt(student.id, "statistics", 2, 2)
    assert course_service.get_course(a_id, student.id).completed_lessons == 0
    assert course_service.get_course(b_id, student.id).completed_lessons == 0
    _mistake(student.id, "only-a", a_id)
    _mistake(student.id, "only-b", b_id)
    with session_scope() as session:
        attempts = QuizAttemptRepository(session).list_for_user(student.id)
        assert {attempt.course_id for attempt in attempts} == {None, a_id, b_id}
    own_a = analytics_service.class_overview(teacher_a.id)
    own_b = analytics_service.class_overview(teacher_b.id)
    assert own_a.student_rows[0].attempts == own_b.student_rows[0].attempts == 1
    assert {item["concept"] for item in own_a.top_mistakes} == {"only-a"}
    assert {item["concept"] for item in own_b.top_mistakes} == {"only-b"}
    assert analytics_service.student_detail(teacher_a.id, student.id)["topics"][0]["attempts"] == 1
    with pytest.raises(PermissionError):
        learning_service.record_quiz_attempt(student.id, "statistics", 1, 2, course_id=999)
    learning_service.record_quiz_attempt(student.id, "statistics", 2, 2, course_id=a_id)
    assert course_service.get_course(a_id, student.id).completed_lessons == 1
    assert course_service.get_course(b_id, student.id).completed_lessons == 0
