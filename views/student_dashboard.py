"""Student dashboard: progress, streak, skills, recommended path and AI suggestions."""

from __future__ import annotations

import streamlit as st

from auth import esc
from components import charts
from components.ui_components import (
    badge_card, bar_html, card_grid, current_user_id, empty_state, go_to, metric_card, page_intro, step_card, tone_for,
)
from core.learning_engine import STYLE_LABELS
from services import learning_service, recommendation_service


def student_dashboard_page() -> None:
    page_intro("student", "MY LEARNING", "Student Dashboard",
               "Your progress, strengths and the best next step — updated after every quiz.")
    user_id = current_user_id()
    if user_id is None:
        empty_state("Please log in again to load your personal dashboard.")
        return

    data = learning_service.get_dashboard(user_id)

    # ── headline numbers ─────────────────────────────────────────────────────
    streak = data.streak
    next_xp = f"{data.next_rank_at - data.xp} XP to next rank" if data.next_rank_at else "Top rank reached"
    card_grid([
        metric_card("Overall mastery", f"{data.overall_mastery:.0f}%",
                    "Based on all your quizzes" if data.topics else "Take a quiz to start",
                    tone_for(data.overall_mastery) if data.topics else ""),
        metric_card("Streak", f"{streak.current} day{'s' if streak.current != 1 else ''}",
                    f"Longest {streak.longest} · " + ("done today ✓" if streak.active_today else "study today to keep it")),
        metric_card("XP · Rank", f"{data.xp} XP", f"{data.rank} · {next_xp}"),
        metric_card("Quizzes taken", data.stats.get("attempts", 0),
                    f"{data.stats.get('lessons_completed', 0)} lessons completed"),
    ])

    left, right = st.columns([3, 2], gap="large")

    # ── recommended path ─────────────────────────────────────────────────────
    with left:
        st.markdown("### Your learning path")
        plan = recommendation_service.get_plan(user_id, with_ai_note=bool(st.session_state.get("_coach_note_on")))
        st.caption(plan.summary)
        if plan.steps:
            for step in plan.steps:
                st.markdown(step_card(step.order, step.kind, step.title, step.reason, step.estimated_minutes),
                            unsafe_allow_html=True)
            first = plan.steps[0]
            a, b = st.columns(2)
            if a.button(f"▶ Start: {first.topic_title}", key="dash_start", use_container_width=True, type="primary"):
                go_to("Student Mission", topic=first.topic_title, mission_started=False, mission_step=0)
            if b.button("🤖 Ask the AI coach", key="dash_coach", use_container_width=True):
                st.session_state["_coach_note_on"] = True
                st.rerun()
            if plan.coach_note:
                st.info(f"🤖 {plan.coach_note}")
            elif st.session_state.get("_coach_note_on"):
                st.caption("The AI coach is offline right now — the plan above is still accurate.")
            st.caption(f"About {plan.total_minutes} minutes in total.")
        else:
            empty_state("No steps yet — enrol in a course or take your first quiz.")

        if data.recent_scores:
            st.plotly_chart(charts.score_trend(data.recent_scores), use_container_width=True)

    # ── skills ───────────────────────────────────────────────────────────────
    with right:
        st.markdown("### Skill levels")
        if data.topics:
            st.plotly_chart(charts.mastery_bar([(c.title, c.mastery) for c in data.topics[:8]], "Weakest topics first"),
                            use_container_width=True)
        else:
            empty_state("Your skill levels appear here after your first quiz.")
        if data.skill_scores:
            st.plotly_chart(charts.skill_radar(data.skill_scores), use_container_width=True)

        style, why = data.learning_style
        style_text = STYLE_LABELS.get(style) or (why if style in ("", "unknown") else style)
        pace = data.speed
        pace_text = pace.label if pace.pace == "unknown" else f"{pace.label} · answers at a {pace.pace} pace"
        st.markdown(
            f"<div class='pl-card'><div class='lbl'>Learning profile</div>"
            f"<div class='sub'>Style: <b>{esc(style_text)}</b></div>"
            f"<div class='sub'>Progress: <b>{esc(pace_text)}</b></div></div>", unsafe_allow_html=True)

    # ── focus areas ──────────────────────────────────────────────────────────
    if data.weak_concepts:
        st.markdown("### Focus areas")
        for topic, concept, mastery in data.weak_concepts[:5]:
            st.markdown(f"<div class='pl-card' style='margin-bottom:8px'><b>{esc(concept)}</b> "
                        f"<span class='sub'>in {esc(topic)} · {mastery:.0f}%</span>{bar_html(mastery, tone_for(mastery))}</div>",
                        unsafe_allow_html=True)

    # ── achievements ─────────────────────────────────────────────────────────
    st.markdown("### Achievements")
    if data.achievements:
        cols = st.columns(3)
        for i, (icon, title, description) in enumerate(data.achievements):
            cols[i % 3].markdown(badge_card(icon, title, description), unsafe_allow_html=True)
    else:
        empty_state("Complete your first quiz to unlock your first badge.")
