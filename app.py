"""
app.py — Streamlit entry point (UI shell only).

Responsibilities: page config, theme, start-up (database, demo users, catalogue), session
restore, sidebar navigation and routing.  All business logic lives in ``services/`` and ``core/``.

Run with:  ``streamlit run app.py``   (``streamlit_app.py`` is a thin alias for deployments)
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Preluma — Light Up Before Class", page_icon="💡", layout="wide")

from config import load_streamlit_secrets_into_env

load_streamlit_secrets_into_env()          # must run before any module reads configuration

from auth import ensure_demo_users, esc                              # noqa: E402
from components import session_bridge                                 # noqa: E402
from components.theme import APP_VERSION, SIDEBAR_URI, inject_theme   # noqa: E402
from database.connection import init_db                               # noqa: E402
from services.homework_service import notifications_for_student, seed_homework_demo  # noqa: E402
from services import ai_service                                       # noqa: E402
from services.course_service import ensure_default_catalog            # noqa: E402
from services.media_service import supabase_enabled                   # noqa: E402
from views.about import demo_guide, evidence_board, professor_defense, project_team, roadmap  # noqa: E402
from views.admin import admin_panel_page                              # noqa: E402
from views.ai_tutor import ai_tutor_page                              # noqa: E402
from views.ai_tutor_legacy import ask_preluma_ai_page                 # noqa: E402
from views.analytics import analytics_page                            # noqa: E402
from views.class_dashboard import class_dashboard_page                # noqa: E402
from views.courses import courses_page                                # noqa: E402
from views.home import home_page                                      # noqa: E402
from views.homework import homework_center_page, my_homework_page     # noqa: E402
from views.login import login_page                                    # noqa: E402
from views.mission import student_mission                             # noqa: E402
from views.profile import student_profile_page, teacher_detail_page, teacher_profile_page  # noqa: E402
from views.projects import student_project_page, teacher_project_page  # noqa: E402
from views.student_dashboard import student_dashboard_page            # noqa: E402
from views.teacher_dashboard import teacher_dashboard_page            # noqa: E402
from views.teacher_studio import teacher_studio                       # noqa: E402

# Pages by audience.  Admins can open everything.
STUDENT_PAGES = {"Dashboard", "Courses", "AI Tutor", "My Progress", "Student Mission", "My Homework",
                 "Ask Preluma AI", "My Profile", "Class Projects", "Professor Defense", "Demo Guide", "Future Roadmap"}
TEACHER_PAGES = {"Teacher Dashboard", "Class Analytics", "Teacher Profile", "Teacher Studio", "Homework Center",
                 "Class Dashboard", "Project Center", "teacher_detail"}
LEARN_GROUP = {"Dashboard", "Courses", "AI Tutor", "My Progress", "Student Mission", "My Homework",
               "Ask Preluma AI", "Class Projects"}
TEACH_GROUP = {"Teacher Dashboard", "Class Analytics", "Teacher Profile", "Teacher Studio", "Homework Center",
               "Class Dashboard", "Project Center"}


@st.cache_resource(show_spinner=False)
def bootstrap() -> bool:
    """One-time (per server process) start-up: tables, demo accounts, default courses."""
    init_db()
    ensure_demo_users()
    ensure_default_catalog()
    return True


def init_state() -> None:
    """Default session-state values (never overwrites existing ones)."""
    defaults = {
        "logged_in": False, "user_role": "", "username": "", "student": "", "user_id": None, "is_admin": False,
        "topic": "Quantum Mechanics", "persona": "Normal Mode", "tutor_history": [], "score_history": [],
        "mission_started": False, "mission_step": 0, "practice_reflection": "", "homework_result": None,
        "selected_homework_id": None, "ai_context_note": "", "_ai_input_key": 0, "_hw_study_mode": False,
        "_hw_chat_history": [], "_hw_input_key": 0, "_hw_chat_topic": "", "_hw_chat_weak": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    seed_homework_demo()


def logout() -> None:
    """End the server session, clear the browser token and all session state."""
    session_bridge.forget()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def _nav_button(label: str, page_name: str, badge: str = "", in_expander: bool = False) -> None:
    display = f"{label}  {badge}".rstrip() if badge else label
    active = st.session_state.get("active_page") == page_name
    button = st.button if in_expander else st.sidebar.button
    if button(display, key=f"nav_{page_name}", use_container_width=True, type="primary" if active else "secondary"):
        st.session_state.active_page = page_name
        try:
            st.query_params["page"] = page_name
        except Exception:  # nosec B110
            pass
        st.rerun()


def sidebar() -> str:
    """Render the navigation; returns the active page name."""
    st.session_state.setdefault("active_page", "Home")
    if SIDEBAR_URI:
        st.sidebar.markdown(
            "<style>[data-testid='stSidebar'] > div:first-child {background: linear-gradient(180deg,"
            "rgba(2,8,16,.93) 0%,rgba(2,8,16,.58) 36%,rgba(2,8,16,.70) 66%,rgba(2,8,16,.94) 100%),"
            f"url('{SIDEBAR_URI}') 43% 52% / cover no-repeat !important;}}</style>",
            unsafe_allow_html=True,
        )
    st.sidebar.markdown("<div class='sb-brand'><div class='sb-brand-name'>Preluma</div>"
                        "<div class='sb-brand-tag'>Light Up Before Class</div></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sb-nav-wrap'>", unsafe_allow_html=True)

    role = st.session_state.get("user_role", "student")
    is_admin = bool(st.session_state.get("is_admin"))
    name = st.session_state.get("student", "") or "Guest"
    unread = len(notifications_for_student(name, unread_only=True)) if role == "student" else 0
    role_color, role_label = ("#67e8f9", "TEACHER") if role == "teacher" else ("#86efac", "STUDENT")
    if is_admin:
        role_color, role_label = "#fbbf24", "ADMIN"
    badge_html = f"<span class='sb-badge'>{unread}</span>" if unread else ""
    initials = "".join(part[0] for part in name.split()[:2] if part).upper() or "PL"
    st.sidebar.markdown(
        "<div class='sb-student-chip'>"
        f"<span class='sb-avatar' aria-hidden='true'>{esc(initials)}</span>"
        "<div style='min-width:0;flex:1'>"
        f"<div class='sb-student-name'>{esc(name)} {badge_html}</div>"
        f"<div class='sb-student-sub' style='color:{role_color}'>{role_label} account</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    current = st.session_state.get("active_page", "Home")
    hw_badge = f" [{unread}]" if unread else ""
    _nav_button("Home", "Home")

    if role == "student" or is_admin:
        _nav_button("Dashboard", "Dashboard")
        _nav_button("My Profile", "My Profile")
        with st.sidebar.expander("LEARN", expanded=current in LEARN_GROUP):
            _nav_button("Courses", "Courses", in_expander=True)
            _nav_button("AI Tutor", "AI Tutor", in_expander=True)
            _nav_button("Student Mission", "Student Mission", in_expander=True)
            _nav_button(f"My Homework{hw_badge}", "My Homework", in_expander=True)
            _nav_button("My Progress", "My Progress", in_expander=True)
            _nav_button("Ask Preluma AI", "Ask Preluma AI", in_expander=True)
            _nav_button("Class Projects", "Class Projects", in_expander=True)

    if role == "teacher" or is_admin:
        _nav_button("Teacher Dashboard", "Teacher Dashboard")
        with st.sidebar.expander("TEACH", expanded=current in TEACH_GROUP):
            _nav_button("Class Analytics", "Class Analytics", in_expander=True)
            _nav_button("Teacher Profile", "Teacher Profile", in_expander=True)
            _nav_button("Teacher Studio", "Teacher Studio", in_expander=True)
            _nav_button("Homework Center", "Homework Center", in_expander=True)
            _nav_button("Class Dashboard", "Class Dashboard", in_expander=True)
            _nav_button("Project Center", "Project Center", in_expander=True)

    _nav_button("About Us", "Project Team")
    if is_admin:
        _nav_button("⚙️ Admin Panel", "Admin Panel")
    if st.sidebar.button("Log Out", key="logout_btn", use_container_width=True, type="secondary"):
        logout()

    live = ai_service.llm_available()
    label = f"AI: {ai_service.active_provider()}" if live else "AI: offline tutor"
    status_class = "sb-status" if live else "sb-status is-offline"
    storage = "Supabase backup on" if supabase_enabled() else "Local storage"
    st.sidebar.markdown(
        f"<div class='{status_class}' role='status'>"
        f"<span class='sb-status-dot'></span><span class='sb-status-text'>{esc(label)}</span>"
        f"<div class='sb-storage'>{esc(storage)} · v{esc(APP_VERSION)}</div></div>",
        unsafe_allow_html=True,
    )
    return st.session_state.active_page


def restore_login() -> None:
    """Revalidate the current server session or restore a demo browser session."""
    if st.session_state.get("logged_in"):
        if session_bridge.refresh_current_user():
            return
    user = session_bridge.try_restore()
    if user is not None:
        session_bridge.apply_user(user)
        st.session_state.setdefault("active_page", "Home")
        st.rerun()
    session_bridge.request_restore()


ROUTES = {
    "Home": home_page,
    "Dashboard": student_dashboard_page,
    "Courses": courses_page,
    "AI Tutor": ai_tutor_page,
    "My Progress": analytics_page,
    "My Profile": student_profile_page,
    "Student Mission": lambda: student_mission(True),
    "My Homework": my_homework_page,
    "Class Projects": student_project_page,
    "Ask Preluma AI": ask_preluma_ai_page,
    "Teacher Dashboard": teacher_dashboard_page,
    "Class Analytics": analytics_page,
    "Teacher Profile": teacher_profile_page,
    "teacher_detail": teacher_detail_page,
    "Teacher Studio": teacher_studio,
    "Homework Center": homework_center_page,
    "Class Dashboard": class_dashboard_page,
    "Project Center": teacher_project_page,
    "Evidence Board": evidence_board,
    "Professor Defense": professor_defense,
    "Project Team": project_team,
    "Demo Guide": demo_guide,
    "Future Roadmap": roadmap,
    "Admin Panel": admin_panel_page,
}


def allowed(page: str) -> bool:
    """Role guard: students and teachers only see their own pages (admins see all)."""
    if st.session_state.get("is_admin"):
        return True
    role = st.session_state.get("user_role", "student")
    if role == "teacher":
        return page not in STUDENT_PAGES
    return page not in TEACHER_PAGES and page != "Admin Panel"


def main() -> None:
    bootstrap()
    inject_theme()
    init_state()

    if not st.session_state.get("_page_restored"):
        try:
            requested = st.query_params.get("page", "")
            if requested in ROUTES:
                st.session_state.active_page = requested
        except Exception:  # nosec B110
            pass
        st.session_state["_page_restored"] = True

    restore_login()
    if not st.session_state.get("logged_in"):
        login_page()
        return

    page = sidebar()
    if page not in ROUTES or not allowed(page):
        page = "Home"
        st.session_state.active_page = page
    ROUTES[page]()


main()
