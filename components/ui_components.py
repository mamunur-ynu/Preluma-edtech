"""
components/ui_components.py — small reusable widgets (cards, bars, pills, page headers).

All user-supplied text MUST go through ``esc()`` before it is placed in HTML; the helpers
below escape their arguments for you.
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from auth.validation import esc
from components.theme import CAMPUS_URI
from core.topics import TOPICS
from services import ai_service

_provider = ai_service.active_provider


def tone_for(value: float, *, weak: float = 60.0, strong: float = 75.0) -> str:
    """Map a 0–100 score to a colour name used by the CSS classes."""
    if value >= strong:
        return "good"
    if value >= weak:
        return "warn"
    return "bad"


def metric_card(label: str, value: object, sub: str = "", tone: str = "") -> str:
    """HTML for one KPI card (put several inside :func:`card_grid`)."""
    return (f"<div class='pl-card {esc(tone)}'><div class='lbl'>{esc(label)}</div>"
            f"<div class='val'>{esc(value)}</div><div class='sub'>{esc(sub)}</div></div>")


def card_grid(cards: Iterable[str], columns: int = 4) -> None:
    st.markdown(f"<div class='pl-grid c{int(columns)}'>{''.join(cards)}</div>", unsafe_allow_html=True)


def section_heading(kicker: str, title: str, subtitle: str = "") -> str:
    """Accessible, reusable section heading for premium dashboard surfaces."""
    description = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    return (
        "<header class='home-section-head'>"
        f"<span>{esc(kicker)}</span><h2>{esc(title)}</h2>{description}"
        "</header>"
    )


def home_metric_card(value: object, label: str, tone: str) -> str:
    """Compact homepage metric card with a constrained visual tone."""
    return (
        f"<article class='home-metric tone-{esc(tone)}'>"
        f"<strong>{esc(value)}</strong><span>{esc(label)}</span>"
        "</article>"
    )


def home_feature_card(order: int, title: str, description: str, tone: str) -> str:
    """Homepage feature card used by both student and teacher feature groups."""
    return (
        f"<article class='home-feature tone-{esc(tone)}'>"
        f"<span class='home-feature-index'>{int(order):02d}</span>"
        f"<h3>{esc(title)}</h3><p>{esc(description)}</p>"
        "</article>"
    )


def home_process_step(order: int, title: str, description: str, tone: str) -> str:
    """One step in the responsive homepage learning workflow."""
    return (
        f"<article class='home-process-step tone-{esc(tone)}'>"
        f"<span>Step {int(order)}</span><h3>{esc(title)}</h3><p>{esc(description)}</p>"
        "</article>"
    )


def bar_html(percent: float, tone: str = "") -> str:
    pct = max(0.0, min(100.0, float(percent)))
    return f"<div class='pl-bar {esc(tone)}'><span style='width:{pct:.0f}%'></span></div>"


def pill(text: str, tone: str = "") -> str:
    return f"<span class='pl-pill {esc(tone)}'>{esc(text)}</span>"


def step_card(order: int, kind: str, title: str, reason: str, minutes: int) -> str:
    css_kind = {"revise": "revise", "practice": "practice", "advance": "next"}.get(kind, "")
    return (f"<div class='pl-step {css_kind}'><div class='n'>{int(order)}</div><div>"
            f"<div class='t'>{esc(title)}</div><div class='r'>{esc(reason)} · ~{int(minutes)} min</div></div></div>")


def badge_card(icon: str, title: str, description: str) -> str:
    return (f"<div class='pl-badge'><span class='ic'>{esc(icon)}</span><div>"
            f"<div class='nm'>{esc(title)}</div><div class='ds'>{esc(description)}</div></div></div>")


def source_note(rank: int, title: str, source: str = "") -> str:
    extra = f" — {esc(source)}" if source else ""
    return f"<div class='pl-src'>[{int(rank)}] {esc(title)}{extra}</div>"


def empty_state(message: str) -> None:
    st.markdown(f"<div class='pl-card'><div class='sub'>{esc(message)}</div></div>", unsafe_allow_html=True)


def hero():
    bg = f"url('{CAMPUS_URI}')" if CAMPUS_URI else "linear-gradient(135deg,#020617,#0f172a,#1e1b4b)"
    provider = _provider()
    ai_pill = f"<span class='ai-pill'>AI: {provider}</span>" if provider != "none" else ""

    st.markdown(f"""
    <div class='hero' style="background-image:{bg};">
      <div class='hero-overlay'></div>
      <div class='hero-content'>
        <div class='hero-top'>
          <div class='logo-mark'>
            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div><div class='brand-name'>Preluma</div><div class='brand-tag'>Light Up Before Class</div></div>
          <div class='uni-pill'>Yunnan University</div>
          {ai_pill}
        </div>
        <div class='hero-badge'>Pre-class brain priming system</div>
        <h1>Prepare before class.<br><span>Understand more during class.</span></h1>
        <div class='hero-sub'>Built for Yunnan University students. Preluma turns passive pre-class preparation into a guided, AI-powered learning mission with Brain Brief, Quiz, UltraTutor, and Smart Class Questions.</div>
        <div class='hero-stats'>
          <div><div class='hero-stat-num'>{len(TOPICS)}</div><div class='hero-stat-lbl'>Curated Topics</div></div>
          <div><div class='hero-stat-num'>4</div><div class='hero-stat-lbl'>Skill Checks</div></div>
          <div><div class='hero-stat-num'>AI</div><div class='hero-stat-lbl'>Smart Tutor</div></div>
          <div><div class='hero-stat-num'>CSV</div><div class='hero-stat-lbl'>Data Persistence</div></div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def page_intro(theme: str, kicker: str, title: str, subtitle: str) -> None:
    """Render a consistent brand header with a page-specific visual identity."""
    st.markdown(
        f"""
        <section class="page-intro theme-{theme}">
            <div class="page-kicker">{kicker}</div>
            <h1 class="page-title">{title}</h1>
            <div class="page-subtitle">{subtitle}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

def progress_bar():
    has_brief = "brief" in st.session_state
    has_quiz  = "quiz_result" in st.session_state
    has_tutor = bool(st.session_state.get("tutor_history"))
    steps = [
        ("Choose Topic", True,      False),
        ("Brain Brief",  has_brief, not has_brief),
        ("Quiz",         has_quiz,  has_brief and not has_quiz),
        ("UltraTutor",   has_tutor, has_quiz  and not has_tutor),
        ("Class Ready",  has_tutor, False),
    ]
    html = "<div class='progress-wrap'>"
    for label, done, active in steps:
        c = "done" if done else ("active" if active else "")
        prefix = "[v] " if done else ""
        html += f"<div class='progress-step {c}'>{prefix}{label}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def chip_row():
    labels = ["Topic","Brain Brief","All Concepts","Quiz","Mistake Clinic","UltraTutor","Class Questions","Readiness Score"]
    st.markdown("<div class='chip-row'>" + "".join(f"<span class='chip'>{label}</span>" for label in labels) + "</div>", unsafe_allow_html=True)


def get_photo_src(photo_key: str) -> str | None:
    """Session-cached profile photo lookup (see ``services.media_service``)."""
    from services import media_service

    cache_key = f"_photo_{photo_key}"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]
    src = media_service.get_photo_uri(photo_key)
    if src:                                  # don't cache misses: a transient failure should retry
        st.session_state[cache_key] = src
    return src


def go_to(page: str, **state: object) -> None:
    """Navigate to another page (optionally pre-filling session-state values) and rerun."""
    if page != "Student Mission" or "mission_course_id" not in state:
        st.session_state.pop("mission_course_id", None)
        st.session_state.pop("mission_course_topic", None)
    for key, value in state.items():
        st.session_state[key] = value
    st.session_state.active_page = page
    try:
        st.query_params["page"] = page
    except Exception:  # nosec B110
        pass
    st.rerun()


def current_user_id() -> int | None:
    """The signed-in user's database id (``None`` for sessions from before the DB existed)."""
    value = st.session_state.get("user_id")
    return int(value) if value else None
