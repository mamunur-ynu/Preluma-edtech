from components.theme import APP_VERSION, UI_REFINEMENT_CSS
from components.ui_components import home_feature_card, section_heading, source_note


def test_reusable_cards_escape_untrusted_content():
    payload = '<img src=x onerror="alert(1)">'
    for rendered in (
        home_feature_card(1, payload, payload, "cyan"),
        section_heading(payload, payload, payload),
        source_note(1, payload, payload),
    ):
        assert payload not in rendered
        assert "&lt;img" in rendered


def test_theme_exposes_keyboard_and_motion_accessibility_contracts():
    assert ":focus-visible" in UI_REFINEMENT_CSS
    assert "prefers-reduced-motion" in UI_REFINEMENT_CSS
    assert APP_VERSION == "5.1"
