"""Regression checks for the two visual identity assets required by Preluma."""

from __future__ import annotations

import hashlib

from components.theme import CAMPUS_IMAGE, CAMPUS_URI, SIDEBAR_IMAGE, SIDEBAR_URI


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
