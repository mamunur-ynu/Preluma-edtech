"""Login, registration and password-recovery screen."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from auth import AuthUser, login, register, register_teacher, reset_password_with_code
from components import session_bridge
from services.user_service import student_number



def _login_bg_css(role: str = "Student") -> str:
    """Load assets/bg_login.jpg as base64 for CSS background. Falls back to gradient."""
    bg_path = Path("assets/bg_login.jpg")
    if bg_path.exists():
        b64 = base64.b64encode(bg_path.read_bytes()).decode()
        bg_val = f"url('data:image/jpeg;base64,{b64}')"
    else:
        bg_val = "linear-gradient(135deg,#0f172a 0%,#1e293b 100%)"
    # Python decides colors — 100% reliable, no CSS selector guessing
    if role == "Teacher":
        pri_bg     = "linear-gradient(135deg,#6366f1,#4f46e5)"
        pri_shadow = "0 0 0 3px rgba(129,140,248,0.35), 0 6px 20px rgba(99,102,241,0.4)"
        sec_bg     = "rgba(16,185,129,0.08)"
        sec_border = "rgba(16,185,129,0.40)"
        sec_color  = "rgba(110,231,183,0.60)"
    else:  # Student active
        pri_bg     = "linear-gradient(135deg,#10b981,#059669)"
        pri_shadow = "0 0 0 3px rgba(52,211,153,0.35), 0 6px 20px rgba(16,185,129,0.4)"
        sec_bg     = "rgba(99,102,241,0.08)"
        sec_border = "rgba(99,102,241,0.40)"
        sec_color  = "rgba(165,163,255,0.60)"
    # Role toggle button colors (col1=Teacher, col2=Student)
    col1_bg     = pri_bg     if role == "Teacher" else sec_bg
    col1_color  = "#fff"     if role == "Teacher" else sec_color
    col1_border = "transparent" if role == "Teacher" else sec_border
    col1_shadow = pri_shadow if role == "Teacher" else "none"
    col2_bg     = pri_bg     if role == "Student" else sec_bg
    col2_color  = "#fff"     if role == "Student" else sec_color
    col2_border = "transparent" if role == "Student" else sec_border
    col2_shadow = pri_shadow if role == "Student" else "none"

    return f"""
<style>
/* ── Background — full viewport, image visible ── */
[data-testid="stAppViewContainer"] {{
    background: {bg_val} center top / cover no-repeat !important;
    min-height: 100vh !important;
}}
[data-testid="stAppViewContainer"]::before {{
    content:""; position:fixed; inset:0;
    background: linear-gradient(to bottom,
        rgba(0,5,18,0.22) 0%,
        rgba(0,5,18,0.30) 50%,
        rgba(0,5,18,0.48) 100%);
    z-index:0;
}}
[data-testid="stHeader"]    {{ background:transparent !important; box-shadow:none !important; }}
[data-testid="stSidebar"]   {{ display:none !important; }}
[data-testid="stDecoration"]{{ display:none !important; }}
[data-testid="stStatusWidget"] {{ display:none !important; }}

/* ── Remove ALL Streamlit internal top whitespace ── */
[data-testid="stMain"] {{ padding-top: 0 !important; padding-bottom: 0 !important; }}
[data-testid="stAppViewBlockContainer"] {{ padding-top: 0 !important; }}
section.main .block-container {{ padding-top: 0 !important; }}
[data-testid="stMain"] .block-container > div:first-child {{ margin-top: 0 !important; padding-top: 0 !important; }}
[data-testid="stVerticalBlock"] > div:first-child {{ margin-top: 0 !important; }}

/* ── FIXED position card — always sits in staircase, never covers building ── */
[data-testid="stMain"] .block-container {{
    position: fixed !important;
    top: 45vh !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 78vw !important;
    max-width: 78vw !important;
    max-height: 54vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    margin: 0 !important;
    padding: 10px 40px 10px !important;
    background: rgba(4,10,28,0.55) !important;
    backdrop-filter: blur(28px) saturate(1.5) !important;
    -webkit-backdrop-filter: blur(28px) saturate(1.5) !important;
    border: 1px solid rgba(255,255,255,0.13) !important;
    border-top: 1px solid rgba(255,255,255,0.22) !important;
    border-radius: 20px !important;
    box-shadow: 0 20px 60px rgba(0,0,0,0.50),
                inset 0 1px 0 rgba(255,255,255,0.10) !important;
    z-index: 999 !important;
}}

/* ── Logo — compact ── */
.login-logo {{ text-align:center; margin-bottom:6px; }}
.login-logo-name {{
    font-size:26px; font-weight:900; color:#67e8f9;
    letter-spacing:-1px; line-height:1;
    text-shadow: 0 0 30px rgba(103,232,249,0.6), 0 0 12px rgba(103,232,249,0.3);
}}
.login-logo-tag  {{
    font-size:9px; color:rgba(255,255,255,0.50); font-weight:600;
    letter-spacing:.13em; margin-top:3px;
}}
.login-logo-univ {{
    font-size:8.5px; color:rgba(255,255,255,0.28); letter-spacing:.04em; margin-top:1px;
}}

/* ── Compact spacing so everything fits in 57vh ── */
.stTextInput {{ margin-bottom: -10px !important; }}
.stTextInput label {{ margin-bottom: 1px !important; font-size: 11px !important; }}
.stTextInput input {{ font-size: 13px !important; padding: 6px 10px !important; }}
[data-testid="stCheckbox"] {{ margin-top: -4px !important; margin-bottom: -4px !important; }}
[data-testid="stCheckbox"] label {{ font-size: 12px !important; }}
[data-testid="stFormSubmitButton"] {{ margin-top: 4px !important; }}
[data-testid="stFormSubmitButton"] button {{ padding: 0.3rem 1rem !important; font-size: 13px !important; }}
.stTabs [data-baseweb="tab-list"] {{ margin-bottom: -6px !important; }}
.stTabs [data-baseweb="tab"] {{ font-size: 12px !important; padding: 6px 12px !important; }}
div[data-testid="stForm"] {{ padding: 10px 12px 8px !important; border-radius: 12px !important; }}
details {{ border-radius: 10px !important; }}
.streamlit-expanderHeader {{ font-size: 12px !important; padding: 6px 12px !important; }}

/* ── Hide "Press Enter to submit form" tooltip ── */
[data-testid="InputInstructions"] {{ display: none !important; }}
small.st-emotion-cache-1gulkj5 {{ display: none !important; }}

/* ── Form submit (Log In / Reset) → cyan ── */
[data-testid="stFormSubmitButton"] button {{
    background: linear-gradient(135deg,#0891b2,#0e7490) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-weight: 700 !important;
    letter-spacing: .06em !important;
    box-shadow: 0 4px 20px rgba(8,145,178,.35) !important;
    padding: 0.5rem 1rem !important;
    width: 100% !important;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    opacity: 0.86 !important;
    box-shadow: 0 6px 32px rgba(8,145,178,0.55) !important;
}}

/* ── Eye icon — transparent (stPasswordField, not stButton wrapper) ── */
[data-testid="stPasswordField"] button {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 8px !important;
    color: rgba(255,255,255,0.45) !important;
    border-radius: 8px !important;
    width: auto !important;
    font-weight: normal !important;
    font-size: inherit !important;
    letter-spacing: normal !important;
}}
[data-testid="stPasswordField"] button:hover {{
    background: rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.8) !important;
    opacity: 1 !important;
}}

/* ── Checkbox → match active role color dynamically (use cyan as neutral) ── */
[data-testid="stCheckbox"] span[data-baseweb="checkbox"] > div {{
    background-color: #0891b2 !important;
    border-color: #0891b2 !important;
}}

/* ── Inputs ── */
.stTextInput > div > div > input {{
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 11px !important;
    color: #f1f5f9 !important;
    font-size: 14px !important;
    transition: border-color .18s, box-shadow .18s !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: rgba(103,232,249,0.6) !important;
    box-shadow: 0 0 0 3px rgba(103,232,249,0.13) !important;
    background: rgba(255,255,255,0.10) !important;
}}
.stTextInput label {{ color:rgba(255,255,255,0.62) !important; font-size:13px !important; font-weight:500 !important; }}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{ background:transparent !important; border-bottom:1px solid rgba(255,255,255,0.10) !important; }}
.stTabs [data-baseweb="tab"] {{ color:rgba(255,255,255,0.42) !important; font-size:13px !important; }}
.stTabs [aria-selected="true"] {{ color:#67e8f9 !important; border-bottom-color:#67e8f9 !important; }}

/* ── Expander (Forgot Password) ── */
details {{ border:1px solid rgba(255,255,255,0.09) !important; border-radius:12px !important; background:rgba(255,255,255,0.03) !important; }}
.streamlit-expanderHeader {{ color:rgba(255,255,255,0.50) !important; font-size:13px !important; }}

/* ── Text / labels ── */
.stMarkdown p {{ color:rgba(255,255,255,0.62) !important; }}
label, .stCheckbox span {{ color:rgba(255,255,255,0.58) !important; }}

/* ── Cred / invite boxes ── */
.cred-box {{
    background:rgba(103,232,249,.05); border:1px solid rgba(103,232,249,.14);
    border-radius:12px; padding:12px 16px; margin-top:14px;
}}
.cred-title {{ font-size:10px; font-weight:800; color:#67e8f9; letter-spacing:.1em; margin-bottom:6px; }}
.cred-row   {{ font-size:11.5px; color:rgba(255,255,255,0.52); line-height:1.9; font-family:monospace; }}
.invite-box {{
    background:rgba(103,232,249,.04); border:1px solid rgba(103,232,249,.13);
    border-radius:12px; padding:12px 16px; margin-bottom:12px;
    font-size:12px; color:rgba(255,255,255,0.48); line-height:1.6;
}}
</style>
"""


def login_page():
    """Beautiful full-screen login & register page with role toggle + invite code."""
    # ── Role from query params (set by HTML button clicks) ───────
    _qp = st.query_params.get("role", "")
    if _qp in ("Teacher", "Student"):
        st.session_state.login_role = _qp
    st.session_state.setdefault("login_role", "Student")
    role = st.session_state.login_role

    st.markdown(_login_bg_css(role), unsafe_allow_html=True)
    st.markdown("""
<div class='login-logo'>
    <div class='login-logo-name'>Preluma</div>
    <div class='login-logo-tag'>LIGHT UP BEFORE CLASS</div>
    <div class='login-logo-univ'>Yunnan University · 云南大学</div>
</div>""", unsafe_allow_html=True)

    # ── Role toggle — HTML anchor buttons, Python inline styles (CSS-free, proven) ──
    t_style = (
        "background:linear-gradient(135deg,#6366f1,#4f46e5);"
        "color:#fff;border:2px solid transparent;"
        "box-shadow:0 0 0 3px rgba(129,140,248,.28),0 4px 16px rgba(99,102,241,.5);"
    ) if role == "Teacher" else (
        "background:rgba(99,102,241,.08);"
        "color:rgba(165,163,255,.65);"
        "border:2px solid rgba(99,102,241,.32);"
    )
    s_style = (
        "background:linear-gradient(135deg,#10b981,#059669);"
        "color:#fff;border:2px solid transparent;"
        "box-shadow:0 0 0 3px rgba(52,211,153,.28),0 4px 16px rgba(16,185,129,.5);"
    ) if role == "Student" else (
        "background:rgba(16,185,129,.08);"
        "color:rgba(110,231,183,.65);"
        "border:2px solid rgba(16,185,129,.32);"
    )
    st.markdown(f"""
<div style="display:flex;gap:10px;margin-bottom:10px;">
  <a href="?role=Teacher" target="_self" style="flex:1;text-decoration:none;">
    <div style="padding:9px 8px;border-radius:10px;
                font-size:12px;font-weight:800;letter-spacing:.08em;
                text-align:center;cursor:pointer;{t_style}">
      TEACHER
    </div>
  </a>
  <a href="?role=Student" target="_self" style="flex:1;text-decoration:none;">
    <div style="padding:9px 8px;border-radius:10px;
                font-size:12px;font-weight:800;letter-spacing:.08em;
                text-align:center;cursor:pointer;{s_style}">
      STUDENT
    </div>
  </a>
</div>
""", unsafe_allow_html=True)


    if role == "Teacher":
        _teacher_panel()
    else:
        _student_panel()


# ── helpers ─────────────────────────────────────────────────────────────────
def _sign_in(user: AuthUser, remember: bool) -> None:
    """Start a revocable server session and optionally persist it in the demo browser."""
    session_bridge.begin_session(user, persist_in_browser=remember)
    st.session_state.active_page = "Home"
    st.rerun()


def _password_reset_form(prefix: str) -> None:
    """Reset with a one-time code that a teacher or administrator hands to the user."""
    with st.expander("Forgot Password?"):
        st.markdown("<p style='font-size:13px;color:#94a3b8;'>Ask your teacher or an administrator for a "
                    "one-time reset code, then set a new password here.</p>", unsafe_allow_html=True)
        with st.form(f"{prefix}_reset_form"):
            uname = st.text_input("Username", key=f"{prefix}_reset_u")
            code = st.text_input("Reset code", key=f"{prefix}_reset_c")
            pw1 = st.text_input("New password", type="password", placeholder="At least 8 characters", key=f"{prefix}_reset_p1")
            pw2 = st.text_input("Confirm new password", type="password", key=f"{prefix}_reset_p2")
            submitted = st.form_submit_button("Reset Password", use_container_width=True)
        if submitted:
            if pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                ok, msg = reset_password_with_code(uname, code, pw1)
                (st.success if ok else st.error)(msg)


def _teacher_panel() -> None:
    st.markdown("""
<div class='invite-box'>
    <b style='color:#67e8f9;'>Teacher Access</b><br>
    Log in below. To create a new teacher account, enter the <b>Teacher Invite Code</b>
    provided by the course admin.
</div>""", unsafe_allow_html=True)
    tab_login, tab_new = st.tabs(["Teacher Log In", "New Teacher? Use Invite Code"])

    with tab_login:
        with st.form("teacher_login_form"):
            c1, c2 = st.columns(2)
            username = c1.text_input("Username", placeholder="Teacher username")
            password = c2.text_input("Password", type="password", placeholder="Password")
            remember = st.checkbox(
                "Keep me logged in",
                value=False,
                disabled=not session_bridge.persistence_available(),
                help=("Enabled only when the deployer opts into the demo-only browser session bridge. "
                      "Production should use an external auth gateway with secure HttpOnly cookies."),
            )
            submitted = st.form_submit_button("Log In as Teacher", use_container_width=True, type="primary")
        if submitted:
            user, reason = login(username, password)
            if user is None:
                st.error(reason)
            elif not user.is_teacher:
                st.error("This is a student account. Please switch to Student mode.")
            else:
                _sign_in(user, remember)
        _password_reset_form("t")

    with tab_new:
        with st.form("teacher_reg_form"):
            name = st.text_input("Full Name", placeholder="Your full name")
            username = st.text_input("Username", placeholder="Choose a username (3–32 characters)")
            pw1 = st.text_input("Password", type="password", placeholder="At least 8 characters")
            pw2 = st.text_input("Confirm Password", type="password")
            code = st.text_input("Teacher Invite Code", type="password", placeholder="Provided by your course admin")
            submitted = st.form_submit_button("Create Teacher Account", use_container_width=True, type="primary")
        if submitted:
            if pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                ok, msg = register_teacher(username, pw1, name, code)
                (st.success if ok else st.error)(msg)


def _student_panel() -> None:
    tab_login, tab_new = st.tabs(["Log In", "New Student? Register Here"])

    with tab_login:
        with st.form("student_login_form"):
            c1, c2 = st.columns(2)
            username = c1.text_input("Username", placeholder="Enter your username")
            password = c2.text_input("Password", type="password", placeholder="Enter your password")
            remember = st.checkbox(
                "Keep me logged in",
                value=False,
                disabled=not session_bridge.persistence_available(),
                help=("Enabled only when the deployer opts into the demo-only browser session bridge. "
                      "Production should use an external auth gateway with secure HttpOnly cookies."),
            )
            submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
        if submitted:
            user, reason = login(username, password)
            if user is None:
                st.error(reason)
            elif user.is_teacher and not user.is_admin:
                st.error("This is a teacher account. Please switch to Teacher mode.")
            else:
                _sign_in(user, remember)
        _password_reset_form("s")

    with tab_new:
        st.markdown("<p style='font-size:12px;color:#64748b;margin-bottom:10px;'>"
                    "Create your student account to track progress and access homework.</p>", unsafe_allow_html=True)
        with st.form("student_reg_form"):
            name = st.text_input("Full Name", placeholder="e.g. Alice Wang")
            username = st.text_input("Username", placeholder="Choose a username (3–32 characters)")
            pw1 = st.text_input("Password", type="password", placeholder="At least 8 characters")
            pw2 = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Student Account", use_container_width=True, type="primary")
        if submitted:
            if pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                ok, msg = register(username, pw1, name, role="student")
                if not ok:
                    st.error(msg)
                else:
                    user, _ = login(username, pw1)
                    if user is not None:
                        number = student_number(user.username)
                        if number:
                            st.success(f"Welcome to Preluma! Your Student ID is **S{number:03d}**.")
                        _sign_in(user, remember=True)
