"""Teacher dashboard: class analytics, weak topics, completion rate and student table."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts
from components.ui_components import card_grid, current_user_id, empty_state, metric_card, page_intro, tone_for
from services import analytics_service, course_service


def teacher_dashboard_page() -> None:
    page_intro("teacher", "CLASS INSIGHTS", "Teacher Dashboard",
               "See who needs help, which topics are hardest and how the class is progressing.")

    actor_id = current_user_id()
    if actor_id is None:
        empty_state("Please log in again to view class analytics.")
        return
    courses = course_service.list_teacher_courses(actor_id)
    labels = {"All students": None, **{f"{c.title} (#{c.id})": c.id for c in courses}}
    c1, c2 = st.columns([2, 1])
    choice = c1.selectbox("Course", list(labels), key="td_course")
    days = c2.selectbox("Period", [7, 14, 30, 90], index=2, format_func=lambda d: f"Last {d} days", key="td_days")

    overview = analytics_service.class_overview(actor_id, labels[choice], days=int(days))
    if overview.students == 0:
        empty_state("No students yet. Once students register (and enrol), their results appear here.")
        return

    card_grid([
        metric_card("Students", overview.students, f"{overview.active_last_7_days} active in the last 7 days"),
        metric_card("Student quiz average", f"{overview.average_mastery:.0f}%", "Each active student weighted equally",
                    tone_for(overview.average_mastery) if overview.average_mastery else ""),
        metric_card("Attempt average", f"{overview.average_quiz_score:.0f}%", f"All recorded quizzes · last {days} days"),
        metric_card("Completion rate", f"{overview.completion_rate:.0f}%", "Lessons completed by enrolled students"),
    ])

    a, b = st.columns(2, gap="large")
    with a:
        if any(d["count"] for d in overview.distribution):
            st.plotly_chart(charts.distribution_bar(overview.distribution, "Student quiz-average distribution"),
                            use_container_width=True)
        else:
            empty_state("The quiz-average distribution appears after students take quizzes in this course.")
    with b:
        if overview.topic_ranking:
            st.plotly_chart(charts.topic_difficulty(overview.topic_ranking, "Hardest topics (class quiz average)"),
                            use_container_width=True)
        else:
            empty_state("Hardest topics appear after students take quizzes.")

    if overview.daily_scores:
        st.plotly_chart(charts.daily_trend(overview.daily_scores), use_container_width=True)
    if overview.top_mistakes:
        st.plotly_chart(charts.mistakes_bar(overview.top_mistakes), use_container_width=True)

    st.markdown("### Students")
    table = pd.DataFrame([
        {"Student": r.name, "Username": r.username, "Quiz average %": r.overall_mastery, "Readiness": r.label,
         "Quizzes": r.attempts, "Last active": r.last_active, "Needs help with": ", ".join(r.weak_topics) or "—"}
        for r in overview.student_rows
    ])
    st.dataframe(table, use_container_width=True, hide_index=True)

    names = {f"{r.name} (@{r.username})": r.user_id for r in overview.student_rows}
    picked = st.selectbox("Drill into a student", ["—"] + list(names), key="td_student")
    if picked != "—":
        detail = analytics_service.student_detail(actor_id, names[picked], labels[choice])
        if detail["topics"]:
            st.plotly_chart(charts.mastery_bar([(t["topic"], t["mastery"]) for t in detail["topics"]],
                                              f"{picked}: quiz averages"),
                            use_container_width=True)
        else:
            st.caption("This student has not taken a quiz yet.")
