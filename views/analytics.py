"""Analytics: class analytics for teachers, personal progress for students."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts
from components.ui_components import current_user_id, empty_state, page_intro
from services import course_service, learning_service
from views.teacher_dashboard import teacher_dashboard_page


def analytics_page() -> None:
    if st.session_state.get("user_role") == "teacher":
        _course_analytics()
    else:
        _my_progress()


def _course_analytics() -> None:
    """Teacher: completion per course, plus the full class dashboard below."""
    page_intro("teacher", "ANALYTICS", "Class Analytics", "Course completion and per-student progress.")
    actor_id = current_user_id()
    if actor_id is None:
        empty_state("Please log in again to view class analytics.")
        return
    courses = course_service.list_teacher_courses(actor_id)
    if courses:
        labels = {f"{c.title} (#{c.id})": c for c in courses}
        picked = st.selectbox("Course", list(labels), key="an_course")
        course = labels[picked]
        rows = course_service.course_completion_report(course.id, actor_id)
        if rows:
            st.plotly_chart(charts.completion_gauge(sum(r["percent"] for r in rows) / len(rows), f"{picked}: average completion"),
                            use_container_width=True)
            st.dataframe(pd.DataFrame(rows).rename(columns={"student": "Student", "username": "Username", "completed": "Done",
                                                            "total": "Lessons", "percent": "Complete %"}),
                         use_container_width=True, hide_index=True)
        else:
            empty_state("Nobody is enrolled in this course yet.")
    st.divider()
    teacher_dashboard_page()


def _my_progress() -> None:
    page_intro("student", "ANALYTICS", "My Progress", "Every topic you've practised, and where you went wrong.")
    user_id = current_user_id()
    if user_id is None:
        empty_state("Please log in again to see your progress.")
        return
    data = learning_service.get_dashboard(user_id)
    if not data.topics:
        empty_state("Take a quiz and your progress charts will appear here.")
        return
    st.plotly_chart(charts.mastery_bar([(c.title, c.mastery) for c in data.topics]), use_container_width=True)
    st.dataframe(pd.DataFrame([{"Topic": c.title, "Mastery %": round(c.mastery), "Level": c.level, "Quizzes": c.attempts,
                                "Trend": f"{c.trend:+.0f}"} for c in data.topics]),
                 use_container_width=True, hide_index=True)
    mistakes = learning_service.recent_mistakes(user_id, 10)
    if mistakes:
        st.markdown("### Recent mistakes to review")
        st.dataframe(pd.DataFrame(mistakes), use_container_width=True, hide_index=True)
