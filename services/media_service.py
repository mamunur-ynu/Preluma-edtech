"""
services/media_service.py — profile photos and profile extras.

Photos are cached on local disk (``photos/``) and, when Supabase is configured, mirrored to the
``preluma_photos`` table so they survive redeploys.  Everything here is best-effort: a network
failure never breaks a page.  Photo keys are validated so they can never escape the folder or
inject into a REST query.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path

from config import get_setting
from security.uploads import UploadPolicy, validate_upload

logger = logging.getLogger("preluma.media")

PHOTOS_DIR = Path("photos")
PHOTO_TABLE = "preluma_photos"
PROFILE_TABLE = "preluma_profiles"
MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
_KEY_RE = re.compile(r"^[a-z0-9_.\-]{1,64}$")


def safe_key(raw: str) -> str:
    """Normalise a photo/profile key (lower-case username).  Raises ``ValueError`` if unsafe."""
    key = str(raw or "").strip().lower()
    if not _KEY_RE.match(key) or ".." in key:
        raise ValueError("Invalid key.")
    return key


def supabase_enabled() -> bool:
    return bool(get_setting("SUPABASE_URL") and get_setting("SUPABASE_KEY"))


def _base(table: str) -> str:
    return f"{get_setting('SUPABASE_URL').rstrip('/')}/rest/v1/{table}"


def _headers(extra: dict | None = None) -> dict:
    key = get_setting("SUPABASE_KEY")
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", **(extra or {})}


# ── photos ───────────────────────────────────────────────────────────────────
def _data_uri(data: bytes, ext: str) -> str:
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64," + base64.b64encode(data).decode()


def load_photo_remote(key: str) -> tuple[bytes | None, str]:
    if not supabase_enabled():
        return None, ""
    try:
        import requests

        rows = requests.get(_base(PHOTO_TABLE), headers=_headers(),
                            params={"photo_key": f"eq.{safe_key(key)}", "select": "photo_data,ext"}, timeout=8).json()
        if rows and isinstance(rows, list):
            return base64.b64decode(rows[0].get("photo_data", "")), str(rows[0].get("ext", "jpg"))
    except Exception as exc:                      # network / decoding problems are not fatal
        logger.info("Remote photo unavailable: %s", exc)
    return None, ""


def get_photo_uri(key: str) -> str | None:
    """Data-URI for a person's photo (local disk first, then Supabase) or ``None``."""
    try:
        key = safe_key(key)
    except ValueError:
        return None
    for ext in ALLOWED_EXTENSIONS:
        path = PHOTOS_DIR / f"{key}.{ext}"
        if path.exists():
            return _data_uri(path.read_bytes(), ext)
    data, ext = load_photo_remote(key)
    if data and ext in ALLOWED_EXTENSIONS:
        try:
            PHOTOS_DIR.mkdir(exist_ok=True)
            (PHOTOS_DIR / f"{key}.{ext}").write_bytes(data)
        except OSError:
            pass
        return _data_uri(data, ext)
    return None


def save_photo(key: str, data: bytes, ext: str) -> tuple[bool, str]:
    """Store a photo locally and (if configured) remotely.  Returns ``(ok, message)``."""
    try:
        key = safe_key(key)
    except ValueError:
        return False, "Invalid photo key."
    ext = ext.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only JPG, PNG or WEBP images are allowed."
    try:
        checked = validate_upload(
            f"photo.{ext}",
            data,
            UploadPolicy(frozenset(f".{item}" for item in ALLOWED_EXTENSIONS), MAX_PHOTO_BYTES, "profile image"),
        )
        data = checked.data
    except ValueError as exc:
        return False, str(exc)
    try:
        PHOTOS_DIR.mkdir(exist_ok=True)
        for old in ALLOWED_EXTENSIONS:
            (PHOTOS_DIR / f"{key}.{old}").unlink(missing_ok=True)
        (PHOTOS_DIR / f"{key}.{ext}").write_bytes(data)
    except OSError as exc:
        return False, f"Could not save the photo: {exc}"
    if supabase_enabled():
        try:
            import requests

            resp = requests.post(_base(PHOTO_TABLE),
                                 headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                                 json={"photo_key": key, "photo_data": base64.b64encode(data).decode(), "ext": ext},
                                 timeout=15)
            if resp.status_code not in (200, 201, 204):
                return True, f"Saved locally; cloud backup failed (HTTP {resp.status_code})."
        except Exception as exc:
            return True, f"Saved locally; cloud backup failed ({type(exc).__name__})."
    return True, ""


def delete_photo(key: str) -> None:
    try:
        key = safe_key(key)
    except ValueError:
        return
    for ext in ALLOWED_EXTENSIONS:
        try:
            (PHOTOS_DIR / f"{key}.{ext}").unlink(missing_ok=True)
        except OSError:
            pass
    if supabase_enabled():
        try:
            import requests

            requests.delete(_base(PHOTO_TABLE), headers=_headers(), params={"photo_key": f"eq.{key}"}, timeout=8)
        except Exception as exc:
            logger.info("Remote photo delete failed: %s", exc)


# ── profile extras (university, major, bio …) ────────────────────────────────
def load_profile_extras(username: str) -> dict:
    if not supabase_enabled():
        return {}
    try:
        import requests

        rows = requests.get(_base(PROFILE_TABLE), headers=_headers(),
                            params={"username": f"eq.{safe_key(username)}", "select": "*"}, timeout=5).json()
        return rows[0] if rows and isinstance(rows, list) else {}
    except Exception as exc:
        logger.info("Profile extras unavailable: %s", exc)
        return {}


def save_profile_extras(username: str, data: dict) -> None:
    if not supabase_enabled():
        return
    try:
        import requests

        requests.post(_base(PROFILE_TABLE), headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                      json={"username": safe_key(username), **data}, timeout=5)
    except Exception as exc:
        logger.info("Profile extras not saved: %s", exc)
