from pathlib import Path


def test_guided_mission_and_homework_pages_exist():
    text = Path("streamlit_app.py").read_text(encoding="utf-8")
    required = [
        "mission_brain_brief_screen",
        "mission_example_screen",
        "mission_practice_screen",
        "mission_mock_test_screen",
        "mission_overview_screen",
        "ask_preluma_ai_page",
        "my_homework_page",
        "homework_center_page",
    ]
    for name in required:
        assert f"def {name}" in text


def test_homework_module_exists():
    assert Path("homework_core.py").exists()
