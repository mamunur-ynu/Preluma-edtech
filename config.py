"""
config.py — central, framework-independent configuration.

Rule of the architecture: **business logic never imports Streamlit.**
Secrets therefore reach the backend through *environment variables only*.
On Streamlit Cloud the secrets live in ``st.secrets``; ``app.py`` calls
:func:`load_streamlit_secrets_into_env` once at start-up to copy them into
``os.environ``.  A future FastAPI backend simply reads the same variables.

Nothing in this module has a hard-coded secret.  Missing optional values
return an empty string; security-critical values (the teacher
invite code) have *no* insecure default — features that need them switch off.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("preluma.config")

PROJECT_ROOT = Path(__file__).resolve().parent

# Names that older versions of Preluma used; we accept both so existing
# Streamlit Cloud secrets keep working after the upgrade.
_ALIASES: dict[str, tuple[str, ...]] = {
    "PRELUMA_TEACHER_INVITE_CODE": ("PRELUMA_TEACHER_INVITE_CODE", "TEACHER_INVITE_CODE"),
}


def get_setting(name: str, default: str = "") -> str:
    """Return a configuration value from the environment (aliases supported)."""
    for candidate in _ALIASES.get(name, (name,)):
        value = os.environ.get(candidate, "").strip()
        if value:
            return value
    return default


def load_streamlit_secrets_into_env() -> None:
    """Copy top-level scalar ``st.secrets`` entries into ``os.environ``.

    Existing environment variables win, so a developer can override a cloud
    secret locally.  Safe to call when Streamlit or the secrets file is absent.
    """
    try:
        import streamlit as st  # imported lazily: only the UI layer may do this

        for key in list(st.secrets.keys()):
            value = st.secrets[key]
            if isinstance(value, (str, int, float, bool)) and str(value).strip():
                os.environ.setdefault(str(key), str(value).strip())
    except Exception:  # no secrets file, or not running under Streamlit
        return


@dataclass(frozen=True)
class Settings:
    """Typed view of the configuration (read fresh on every call)."""

    database_url: str
    data_dir: Path
    session_ttl_seconds: int
    teacher_invite_code: str
    admin_usernames: frozenset[str]
    demo_users: tuple[dict[str, str], ...]
    embedding_backend: str
    vector_backend: str
    llm_timeout_seconds: int
    llm_max_tokens: int
    allow_legacy_browser_session: bool
    ai_requests_per_minute: int
    conversation_retention_days: int

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def _int(name: str, default: int) -> int:
    try:
        return int(get_setting(name, str(default)))
    except ValueError:
        logger.warning("Setting %s is not an integer; using %s", name, default)
        return default


def _bool(name: str, default: bool = False) -> bool:
    raw = get_setting(name)
    if not raw:
        return default
    return raw.casefold() in {"1", "true", "yes", "on"}


def _demo_users() -> tuple[dict[str, str], ...]:
    """Parse ``DEMO_USERS_JSON`` — a JSON list of {username,password,role,full_name}.

    Demo accounts exist for classroom demos only.  They are *never* defined in
    source code; the deployer opts in by supplying this value.
    """
    raw = get_setting("DEMO_USERS_JSON")
    if not raw:
        return ()
    try:
        data: Any = json.loads(raw)
        return tuple(
            {k: str(v) for k, v in item.items()}
            for item in data
            if isinstance(item, dict) and item.get("username") and item.get("password")
        )
    except (ValueError, TypeError, AttributeError):
        logger.warning("DEMO_USERS_JSON is not valid JSON; ignoring it.")
        return ()


def get_settings() -> Settings:
    """Build a :class:`Settings` snapshot from the current environment."""
    data_dir = Path(get_setting("PRELUMA_DATA_DIR", str(PROJECT_ROOT / "data")))
    default_db = f"sqlite:///{(data_dir / 'preluma.db').as_posix()}"
    admins = {
        part.strip().lower()
        for part in get_setting("PRELUMA_ADMIN_USERS").split(",")
        if part.strip()
    }
    return Settings(
        database_url=get_setting("DATABASE_URL", default_db),
        data_dir=data_dir,
        session_ttl_seconds=_int("PRELUMA_SESSION_TTL_HOURS", 24) * 3600,
        teacher_invite_code=get_setting("PRELUMA_TEACHER_INVITE_CODE"),
        admin_usernames=frozenset(admins),
        demo_users=_demo_users(),
        embedding_backend=get_setting("PRELUMA_EMBEDDINGS", "auto").lower(),
        vector_backend=get_setting("PRELUMA_VECTOR_STORE", "auto").lower(),
        llm_timeout_seconds=_int("PRELUMA_LLM_TIMEOUT", 20),
        llm_max_tokens=_int("PRELUMA_LLM_MAX_TOKENS", 2200),
        allow_legacy_browser_session=_bool("PRELUMA_ALLOW_LEGACY_BROWSER_SESSION", False),
        ai_requests_per_minute=max(1, _int("PRELUMA_AI_REQUESTS_PER_MINUTE", 12)),
        conversation_retention_days=max(1, _int("PRELUMA_CONVERSATION_RETENTION_DAYS", 30)),
    )
