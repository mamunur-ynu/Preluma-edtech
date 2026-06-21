from pathlib import Path


APP = Path("streamlit_app.py").read_text(encoding="utf-8")


def test_unique_page_themes_exist():
    for theme in [
        "theme-ai",
        "theme-homework",
        "theme-teacher",
        "theme-evidence",
        "theme-defense",
        "theme-demo",
        "theme-roadmap",
    ]:
        assert theme in APP


def test_sidebar_has_no_navigation_emoji():
    forbidden = ["🎯", "🔔", "✨", "📊", "🏫"]
    sidebar_start = APP.index("def sidebar():")
    sidebar_end = APP.index("# ── Hero", sidebar_start)
    sidebar = APP[sidebar_start:sidebar_end]
    for item in forbidden:
        assert item not in sidebar


def test_team_photo_is_background_hero():
    assert "team-photo-hero" in APP
    assert "background-image:url" in APP
    assert "background-position: center center" in APP


def test_adaptive_ai_paragraph_depth():
    assert 'depth == "Deep"' in APP
    assert '"\\n\\n".join(paragraphs)' in APP
    assert "Adaptive academic tutor" in APP


def test_teacher_profiles_are_not_added_yet():
    assert "Teacher Profile System" not in APP
