"""End-to-end UI smoke tests using Streamlit's AppTest (signed-in student, offline mode)."""

from helpers import logged_in_app


def _click(at, label):
    for button in at.button:
        if button.label == label:
            button.click().run()
            assert len(at.exception) == 0, [e.value for e in at.exception]
            return
    raise AssertionError(f"Button not found: {label}")


def _answer_mock_test(at):
    """Walk through the one-question-at-a-time mock test and submit it."""
    for _ in range(10):
        labels = [b.label for b in at.button]
        if "Submit Mock Test" in labels:
            return _click(at, "Submit Mock Test")
        _click(at, "Next Question →")
    raise AssertionError("Mock test never reached its last question")


def _open_page(at, page):
    at.session_state["active_page"] = page
    at.run()
    assert len(at.exception) == 0, [e.value for e in at.exception]


def test_streamlit_startup_and_guided_flow():
    at = logged_in_app("student", "Student Mission")
    assert len(at.exception) == 0
    for label in ["Start Pre-Class Mission", "See a Real Example →", "Try It Yourself →", "Take the Mock Test →"]:
        _click(at, label)
    _answer_mock_test(at)
    _click(at, "View Final Overview →")
    assert len(at.exception) == 0


def test_quiz_result_is_saved_to_the_learning_database():
    from services import learning_service

    at = logged_in_app("student", "Student Mission")
    for label in ["Start Pre-Class Mission", "See a Real Example →", "Try It Yourself →", "Take the Mock Test →"]:
        _click(at, label)
    _answer_mock_test(at)
    dashboard = learning_service.get_dashboard(at.session_state["user_id"])
    assert dashboard.stats["attempts"] == 1


def test_streamlit_sidebar_pages_open():
    at = logged_in_app("student")
    for page in ["Ask Preluma AI", "My Homework", "Dashboard", "Courses", "AI Tutor", "My Progress"]:
        _open_page(at, page)
    teacher = logged_in_app("teacher")
    for page in ["Homework Center", "Teacher Dashboard", "Class Analytics", "Class Dashboard"]:
        _open_page(teacher, page)
    admin = logged_in_app("admin", "Admin Panel")
    assert len(admin.exception) == 0


def test_students_cannot_open_teacher_pages():
    at = logged_in_app("student")
    _open_page(at, "Teacher Dashboard")
    assert at.session_state["active_page"] == "Home"


def test_teachers_cannot_open_student_only_pages():
    at = logged_in_app("teacher")
    _open_page(at, "My Homework")
    assert at.session_state["active_page"] == "Home"


def test_project_team_page_and_question_aware_ai():
    at = logged_in_app("student")
    _open_page(at, "Project Team")
    assert any("Team Preluma" in (item.value or "") for item in at.markdown)

    _open_page(at, "Ask Preluma AI")
    at.text_area[0].set_value("about machine learning").run()
    _click(at, "Ask Preluma AI")
    assert any("Machine Learning" in (item.value or "") for item in at.markdown)
    assert not any("Variance · Curated" in (item.value or "") for item in at.markdown)
