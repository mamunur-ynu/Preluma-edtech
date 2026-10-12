"""Compatibility service boundary for the legacy homework store.

The legacy implementation remains intact until a verified relational cutover,
but Streamlit views import this service rather than the persistence module.
"""

from homework_core import (
    create_homework,
    create_notification,
    homework_for_student,
    homework_overview,
    hw_num,
    load_all_mistakes,
    load_homework,
    load_questions,
    load_student_mistakes,
    load_submissions,
    mark_notifications_read,
    notifications_for_student,
    seed_homework_demo,
    submit_homework,
    update_homework,
)

__all__ = [
    "create_homework",
    "create_notification",
    "homework_for_student",
    "homework_overview",
    "hw_num",
    "load_all_mistakes",
    "load_homework",
    "load_questions",
    "load_student_mistakes",
    "load_submissions",
    "mark_notifications_read",
    "notifications_for_student",
    "seed_homework_demo",
    "submit_homework",
    "update_homework",
]
