"""Regression checks for the two visual identity assets required by Preluma."""

from __future__ import annotations

import hashlib
import re

from components.theme import CAMPUS_IMAGE, CAMPUS_URI, CSS, SIDEBAR_IMAGE, SIDEBAR_URI, UI_REFINEMENT_CSS


EXPECTED_ASSET_HASHES = {
    "ynu_campus.jpg": "35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc",
    "sidebar_bg.jpg": "3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2",
}


def test_original_identity_images_are_preserved_exactly():
    for image in (CAMPUS_IMAGE, SIDEBAR_IMAGE):
        assert image.is_file()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == EXPECTED_ASSET_HASHES[image.name]


def test_identity_images_are_embedded_for_deployment():
    assert CAMPUS_IMAGE.is_absolute()
    assert SIDEBAR_IMAGE.is_absolute()
    assert CAMPUS_URI.startswith("data:image/jpeg;base64,")
    assert SIDEBAR_URI.startswith("data:image/jpeg;base64,")


def _contrast(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                  for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_streamlit_navigation_and_dashboard_text_remain_readable():
    assert not re.search(r"\[data-testid=['\"]stSidebar['\"]\]\s+label\s*\{[^}]*display:\s*none", CSS)
    assert "summary:focus-visible" in UI_REFINEMENT_CSS
    assert "button:focus-visible" in UI_REFINEMENT_CSS
    for text_color, surface in (
        ("#b9cde2", "#020810"),  # LEARN/TEACH expander labels
        ("#b1c4db", "#020817"),  # homepage metrics and dashboard labels
        ("#a7bad2", "#020817"),  # dashboard secondary copy and footer
    ):
        assert _contrast(text_color, surface) >= 4.5
