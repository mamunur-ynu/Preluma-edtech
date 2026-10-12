"""Administrator panel: accounts, reset codes, system health."""

from __future__ import annotations

import streamlit as st

from auth import esc, issue_reset_code
from config import get_settings
from services import ai_service, user_service
from services.media_service import supabase_enabled
from services.audit_service import read_recent_logs


def admin_panel_page() -> None:
    """Render the administration panel (admins only)."""
    current = st.session_state.get("username", "")
    actor_id = st.session_state.get("user_id")
    if not user_service.is_admin_username(current):
        st.error("Access denied.")
        return

    st.markdown("<div style='padding:24px 0 8px;'><div style='font-size:22px;font-weight:800;color:#e2e8f0;'>"
                "⚙️ Admin Panel</div><div style='font-size:13px;color:#64748b;margin-top:4px;'>"
                "Administrators only</div></div>", unsafe_allow_html=True)

    users = user_service.list_users()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total users", len(users))
    c2.metric("Admins", sum(1 for u in users if u.is_admin))
    c3.metric("Teachers", sum(1 for u in users if u.role == "teacher" and not u.is_admin))
    c4.metric("Students", sum(1 for u in users if u.role == "student"))

    tab_users, tab_health = st.tabs(["Accounts", "System health"])

    with tab_users:
        role_filter = st.selectbox("Filter by role", ["All", "admin", "teacher", "student"], key="admin_filter")
        query = st.text_input("Search by name or username", key="admin_search").strip().lower()
        shown = [u for u in users
                 if (role_filter == "All" or (role_filter == "admin" and u.is_admin)
                     or (role_filter != "admin" and u.role == role_filter and not u.is_admin))
                 and (not query or query in u.username or query in u.full_name.lower())]
        st.caption(f"{len(shown)} users shown")
        for u in shown:
            label = "ADMIN" if u.is_admin else u.role.upper()
            info, reset_col, status_col = st.columns([5, 2, 2])
            info.markdown(
                f"<div style='padding:10px 14px;background:rgba(30,41,59,.6);border-radius:10px;"
                f"border:1px solid rgba(100,116,139,.15);'><b style='color:#e2e8f0'>{esc(u.full_name)}</b> "
                f"<span style='color:#64748b;font-size:12px'>@{esc(u.username)}</span> "
                f"<span class='pl-pill'>{esc(label)}</span></div>", unsafe_allow_html=True)
            if reset_col.button("Reset code", key=f"reset_{u.username}", help="One-time code, valid 30 minutes"):
                ok, result = issue_reset_code(int(actor_id), u.username)
                if ok:
                    st.session_state["_last_reset"] = (u.username, result)
                else:
                    st.error(result)
            if not u.is_admin and status_col.button("Deactivate", key=f"deact_{u.username}"):
                ok, message = user_service.set_active(int(actor_id), u.username, False)
                (st.success if ok else st.error)(message)
        if "_last_reset" in st.session_state:
            who, code = st.session_state["_last_reset"]
            st.info(f"Reset code for **{who}**: `{code}` — give it to the user in person. It expires in 30 minutes.")

    with tab_health:
        settings = get_settings()
        st.write({
            "Database": "SQLite (file)" if settings.is_sqlite else "External SQL database",
            "AI providers configured": ai_service.available_providers() or "none (offline tutor)",
            "Cloud storage (Supabase)": "connected" if supabase_enabled() else "not configured",
            "RAG index": ai_service.rag_stats(),
        })
        st.markdown("**Recent audit log**")
        try:
            logs = read_recent_logs(50)
            if logs:
                st.code("\n".join(logs), language="text")
            else:
                st.caption("No log entries yet.")
        except Exception as exc:  # the log store is optional
            st.caption(f"Log unavailable: {type(exc).__name__}")
