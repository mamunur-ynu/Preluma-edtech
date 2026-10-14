"""Course catalogue: browse, enrol, follow lessons."""

from __future__ import annotations

import streamlit as st

from auth import esc
from components.ui_components import bar_html, current_user_id, empty_state, go_to, page_intro, pill
from core.topics import TOPIC_OPTIONS
from services import course_service
from services._common import title_for

_STATUS = {"completed": ("✓ Done", "good"), "in_progress": ("In progress", "warn"), "not_started": ("Not started", "")}


def courses_page() -> None:
    page_intro("student", "LEARN", "Courses", "Pick a course, enrol, and follow the lessons in order.")
    user_id = current_user_id()
    if user_id is None:
        empty_state("Please log in again to see your courses.")
        return

    selected = st.session_state.get("_course_open")
    if selected:
        _course_detail(user_id, int(selected))
        return

    courses = course_service.list_courses(user_id)
    if not courses:
        empty_state("No courses yet.")
    cols = st.columns(2, gap="large")
    for i, course in enumerate(courses):
        with cols[i % 2]:
            st.markdown(
                f"<div class='pl-card' style='margin-bottom:6px'><div class='lbl'>{esc(course.level)} · "
                f"{course.lesson_count} lessons</div><div class='val' style='font-size:21px'>{esc(course.title)}</div>"
                f"<div class='sub'>{esc(course.description)}</div>"
                f"{bar_html(course.percent) if course.enrolled else ''}</div>", unsafe_allow_html=True)
            label = "Continue" if course.enrolled else "Open"
            if st.button(label, key=f"open_{course.id}", use_container_width=True):
                st.session_state["_course_open"] = course.id
                st.rerun()


def _course_detail(user_id: int, course_id: int) -> None:
    course = course_service.get_course(course_id, user_id)
    if course is None:
        st.session_state.pop("_course_open", None)
        st.rerun()
        return
    if st.button("← All courses", key="back_courses"):
        st.session_state.pop("_course_open", None)
        st.rerun()

    st.markdown(f"## {esc(course.title)}")
    st.caption(f"{course.level} · {course.completed_lessons}/{course.lesson_count} lessons completed")
    st.markdown(bar_html(course.percent), unsafe_allow_html=True)

    if not course.enrolled:
        if st.button("Enrol in this course", type="primary", key="enroll_btn"):
            course_service.enroll(user_id, course.id)
            st.rerun()
        st.caption("Enrol to track progress and get a learning path built around this course.")
    else:
        nxt = course_service.next_lesson(user_id, course.id)
        if nxt and st.button(f"▶ Continue: {nxt.title}", type="primary", key="continue_btn"):
            go_to("Student Mission", topic=_mission_title(nxt.topic_key), mission_started=False,
                  mission_step=0, mission_course_id=course.id, mission_course_topic=nxt.topic_key)

    for lesson in course.lessons:
        label, tone = _STATUS.get(lesson.status, _STATUS["not_started"])
        a, b = st.columns([5, 1])
        a.markdown(
            f"<div class='pl-card' style='margin-bottom:8px'><b>{lesson.order_index}. {esc(lesson.title)}</b> "
            f"{pill(label, tone)}<span class='sub'> ~{lesson.estimated_minutes} min"
            f"{' · best ' + format(lesson.percent, '.0f') + '%' if lesson.percent else ''}</span>"
            f"{'<div class=sub>Builds on: ' + esc(', '.join(lesson.locked_by)) + '</div>' if lesson.locked_by and lesson.status == 'not_started' else ''}"
            f"</div>", unsafe_allow_html=True)
        if course.enrolled and b.button("Start", key=f"start_{lesson.id}", use_container_width=True):
            go_to("Student Mission", topic=_mission_title(lesson.topic_key), mission_started=False,
                  mission_step=0, mission_course_id=course.id, mission_course_topic=lesson.topic_key)


def _mission_title(key: str) -> str:
    """The title the Mission form understands (falls back to the key's display title)."""
    title = title_for(key)
    return title if title in TOPIC_OPTIONS else key.title()
