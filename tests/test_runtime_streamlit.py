from streamlit.testing.v1 import AppTest


def _click(at, label):
    for button in at.button:
        if button.label == label:
            button.click().run()
            assert len(at.exception) == 0
            return
    raise AssertionError(f"Button not found: {label}")


def _open_page(at, page):
    at.session_state["active_page"] = page
    at.run()
    assert len(at.exception) == 0


def test_streamlit_startup_and_guided_flow():
    at = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    assert len(at.exception) == 0
    for label in [
        "Start Pre-Class Mission",
        "See a Real Example →",
        "Try It Yourself →",
        "Take the Mock Test →",
        "Submit Mock Test",
        "View Final Overview →",
    ]:
        _click(at, label)
    assert len(at.exception) == 0


def test_streamlit_sidebar_pages_open():
    at = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    assert len(at.exception) == 0
    for page in ["Ask Preluma AI", "Homework Center", "My Homework"]:
        _open_page(at, page)


def test_project_team_page_and_question_aware_ai():
    at = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    _open_page(at, "Project Team")
    assert any("Team Preluma" in (item.value or "") for item in at.markdown)

    _open_page(at, "Ask Preluma AI")
    at.text_area[0].set_value("about machine learning").run()
    _click(at, "Ask Preluma AI")
    assert any("Machine Learning" in (item.value or "") for item in at.markdown)
    assert not any("Variance · Curated" in (item.value or "") for item in at.markdown)
