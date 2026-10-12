"""Premium home page that preserves Preluma's original campus identity."""

from __future__ import annotations

import streamlit as st

from auth.validation import esc
from components.theme import APP_VERSION, CAMPUS_URI
from components.ui_components import (
    home_feature_card,
    home_metric_card,
    home_process_step,
    section_heading,
)
from core.topics import TOPICS
from services.homework_service import notifications_for_student
from services.ai_service import active_provider


FEATURES = (
    (1, "Student Mission", "A focused five-step path from Brain Brief to class-ready questions.", "cyan"),
    (2, "AI Tutor", "Grounded answers, course sources and conversation memory with an offline fallback.", "indigo"),
    (3, "My Homework", "Assignments, instant feedback, mistake capture and a clear route to revision.", "emerald"),
    (4, "Learning Dashboard", "Mastery, weak concepts, streaks and the next best action in one view.", "amber"),
    (5, "Teacher Workspace", "Publish work, review the class and identify students who need support.", "rose"),
    (6, "Evidence & Analytics", "Transparent algorithms, readiness signals and auditable learning records.", "violet"),
)

PROCESS_STEPS = (
    (1, "Choose a topic", "Start with the next lecture topic or continue your personal learning path.", "indigo"),
    (2, "Build the brief", "Prime your understanding with a concise explanation and real examples.", "cyan"),
    (3, "Practise and adapt", "Use quiz evidence to reveal weak concepts and focus the next activity.", "emerald"),
    (4, "Arrive class-ready", "Ask better questions with AI support and a clear readiness overview.", "amber"),
)


def _go(page: str) -> None:
    """Navigate without coupling the home page to application routing internals."""
    st.session_state.active_page = page
    try:
        st.query_params["page"] = page
    except Exception:  # nosec B110
        pass
    st.rerun()


def _announcement_panel(student: str) -> None:
    """Show recent student announcements with escaped user-managed content."""
    if st.session_state.get("user_role", "student") != "student" or student == "Guest":
        return
    notices = notifications_for_student(student, unread_only=True)
    announcements = [item for item in notices if item.get("Type") == "Announcement"]
    for announcement in announcements[-3:]:
        title = esc(announcement.get("Title", "Announcement"))
        message = esc(announcement.get("Message", ""))
        st.markdown(
            "<aside class='home-announcement' role='status'>"
            "<span class='home-announcement-mark' aria-hidden='true'>i</span>"
            f"<div><strong>{title}</strong><p>{message}</p></div></aside>",
            unsafe_allow_html=True,
        )


def _hero(provider: str) -> None:
    """Render the original Yunnan University image as the authoritative hero."""
    background = f"url('{CAMPUS_URI}')" if CAMPUS_URI else "linear-gradient(135deg,#020617,#0f2747)"
    provider_label = esc(provider.upper()) if provider and provider != "none" else "OFFLINE READY"
    st.markdown(
        f"""
        <section class="home-hero" style="--home-campus-image:{background}" aria-labelledby="home-title">
            <div class="home-hero-content">
                <div class="home-eyebrow"><span></span> Preluma AI &nbsp;·&nbsp; Yunnan University</div>
                <h1 id="home-title">Prepare before class.<br><em>Understand more during class.</em></h1>
                <p>AI-powered pre-class learning with guided missions, adaptive practice,
                   a grounded tutor and clear teacher insight.</p>
                <div class="home-hero-meta" aria-label="Platform status">
                    <span>Light Up Before Class</span>
                    <span class="home-provider"><i></i> AI: {provider_label}</span>
                </div>
            </div>
            <div class="home-hero-caption">Yunnan University campus</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _quick_actions(role: str) -> None:
    st.markdown(
        section_heading("Quick access", "Continue where it matters", "Move directly into your most-used workspace."),
        unsafe_allow_html=True,
    )
    with st.container(key="home_quick_actions"):
        columns = st.columns(4)
        if role == "teacher":
            actions = (
                ("Teacher Dashboard", "Teacher Dashboard", "primary"),
                ("Teacher Studio", "Teacher Studio", "secondary"),
                ("Homework Center", "Homework Center", "secondary"),
                ("Class Analytics", "Class Analytics", "secondary"),
            )
        else:
            actions = (
                ("Start a Mission", "Student Mission", "primary"),
                ("Ask Preluma AI", "AI Tutor", "secondary"),
                ("My Homework", "My Homework", "secondary"),
                ("View Dashboard", "Dashboard", "secondary"),
            )
        for column, (label, page, button_type) in zip(columns, actions):
            if column.button(label, use_container_width=True, type=button_type):
                _go(page)


def home_page() -> None:
    """Render the first signed-in screen without mixing in business logic."""
    provider = active_provider()
    student = st.session_state.get("student", "") or "Guest"
    role = st.session_state.get("user_role", "student")

    _hero(provider)
    _announcement_panel(student)

    metrics = (
        home_metric_card(len(TOPICS), "Curated topics", "cyan"),
        home_metric_card(5, "Mission steps", "indigo"),
        home_metric_card("3+", "Learning algorithms", "emerald"),
        home_metric_card("8", "AI providers", "amber"),
    )
    st.markdown(f"<section class='home-metric-grid'>{''.join(metrics)}</section>", unsafe_allow_html=True)

    st.markdown(
        section_heading(
            "One connected platform",
            "Everything you need before the lecture",
            "A calmer path from first exposure to confident participation in class.",
        ),
        unsafe_allow_html=True,
    )
    cards = "".join(home_feature_card(*feature) for feature in FEATURES)
    st.markdown(f"<section class='home-feature-grid'>{cards}</section>", unsafe_allow_html=True)

    st.markdown(
        section_heading(
            "The learning loop",
            "From unfamiliar to class-ready",
            "Each stage produces evidence that improves the next recommendation.",
        ),
        unsafe_allow_html=True,
    )
    steps = "".join(home_process_step(*step) for step in PROCESS_STEPS)
    st.markdown(f"<section class='home-process'>{steps}</section>", unsafe_allow_html=True)

    _quick_actions(role)

    st.markdown(
        "<footer class='home-footer'>"
        "<span>Preluma · Yunnan University · Python + Streamlit</span>"
        f"<span>Signed in as <strong>{esc(student)}</strong> · v{esc(APP_VERSION)}</span>"
        "</footer>",
        unsafe_allow_html=True,
    )
