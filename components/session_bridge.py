"""
components/session_bridge.py — "remember me" for Streamlit.

Streamlit does not expose a first-party HttpOnly cookie API. Persistent browser restore is
therefore disabled by default. Deployers may explicitly enable the legacy localStorage/query
bridge for a classroom demo, but it is not an acceptable production session transport. The
token remains opaque, server-side, expiring, and revocable; see ``auth.sessions``.
"""

from __future__ import annotations

import re

import streamlit as st
import streamlit.components.v1 as stc

from auth import AuthUser, end_session, start_session, user_for_session
from config import get_settings

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-]{20,128}$")
STORAGE_KEY = "preluma_t"


def _js(body: str) -> None:
    """Run a tiny script in a hidden same-origin frame (it reaches the page via ``parent``).

    Only constant code and validated tokens are ever interpolated into ``body``.
    """
    html = f"<script>try{{{body}}}catch(e){{}}</script>"
    if hasattr(st, "iframe"):                      # Streamlit ≥ 1.5x: st.components.v1.html is deprecated
        st.iframe(html, height=1)
    else:
        stc.html(html, height=0)


def persistence_available() -> bool:
    """Whether the deployer explicitly accepted the legacy demo-only bridge."""
    return get_settings().allow_legacy_browser_session


def begin_session(user: AuthUser, *, persist_in_browser: bool = False) -> bool:
    """Create a revocable server session for every login; optionally persist it for demos."""
    token = start_session(user)
    st.session_state["_session_token"] = token
    apply_user(user)
    if persist_in_browser and persistence_available() and _TOKEN_RE.fullmatch(token):
        _js(f"parent.localStorage.setItem('{STORAGE_KEY}','{token}');")
        return True
    return False


def remember(user: AuthUser) -> bool:
    """Backward-compatible demo helper; every login must use a server session."""
    return begin_session(user, persist_in_browser=True)


def clear_identity() -> None:
    """Remove cached identity; a future rerun must authenticate again."""
    for key in ("_session_token", "logged_in", "user_id", "user_role", "username", "student", "is_admin"):
        st.session_state.pop(key, None)


def refresh_current_user() -> bool:
    """Refresh identity from the revocable server session before a protected page renders."""
    token = st.session_state.get("_session_token", "")
    user = user_for_session(token) if isinstance(token, str) and _TOKEN_RE.fullmatch(token) else None
    if user is None:
        clear_identity()
        return False
    apply_user(user)
    return True


def forget() -> None:
    """Revoke the server session and clear the browser copy."""
    token = st.session_state.pop("_session_token", "")
    if token:
        end_session(token)
    try:
        st.query_params.clear()
    except Exception:  # nosec B110
        pass
    _js(f"parent.localStorage.removeItem('{STORAGE_KEY}');parent.sessionStorage.removeItem('preluma_restored');")


def request_restore() -> None:
    """Ask the browser to reload once with the saved token in the URL (only when logged out)."""
    if not persistence_available():
        return
    _js(
        f"var t=parent.localStorage.getItem('{STORAGE_KEY}');"
        "var p=new URLSearchParams(parent.location.search);"
        "if(t&&!p.has('t')&&!parent.sessionStorage.getItem('preluma_restored')){"
        "parent.sessionStorage.setItem('preluma_restored','1');p.set('t',t);"
        "parent.location.replace(parent.location.pathname+'?'+p.toString());}"
    )


def try_restore() -> AuthUser | None:
    """Resolve a token from the URL (or this session) to a user; remove it from the URL either way."""
    if not persistence_available():
        return None
    token = ""  # nosec B105
    try:
        token = str(st.query_params.get("t", "") or "")
        if token:
            del st.query_params["t"]
    except Exception:  # nosec B110
        pass
    token = token or st.session_state.get("_session_token", "")
    if not token or not _TOKEN_RE.match(token):
        return None
    user = user_for_session(token)
    if user is not None:
        st.session_state["_session_token"] = token
    return user


def apply_user(user: AuthUser) -> None:
    """Copy the signed-in user into ``st.session_state`` (the keys the pages read)."""
    st.session_state.logged_in = True
    st.session_state.user_id = user.id
    st.session_state.user_role = "teacher" if user.role == "admin" else user.role
    st.session_state.username = user.username
    st.session_state.student = user.full_name
    st.session_state.is_admin = user.is_admin
