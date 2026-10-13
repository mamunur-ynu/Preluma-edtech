"""
components/progress_hooks.py — connects the Streamlit quiz screens to the learning database.

The mission and homework screens still write their legacy CSV rows (so nothing that worked
before breaks); these hooks *additionally* record every attempt in the relational database via
``learning_service`` so mastery, streaks, achievements and recommendations stay up to date.
They never raise: a database hiccup must not break a quiz.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping

import streamlit as st

from services import learning_service
from services._common import topic_key

logger = logging.getLogger("preluma.ui")
_T0_KEY = "_quiz_t0"


def mark_quiz_started() -> None:
    """Remember when the student first saw the current quiz (for the learning-speed estimate)."""
    st.session_state.setdefault(_T0_KEY, time.time())


def _elapsed() -> int:
    started = st.session_state.pop(_T0_KEY, None)
    return int(min(max(time.time() - started, 0), 3600)) if started else 0


def record_mission(result: Mapping[str, Any], topic: str) -> None:
    """Save a finished mission quiz (result dict from ``grade()``)."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    try:
        course_id = st.session_state.get("mission_course_id")
        if topic_key(topic) != st.session_state.get("mission_course_topic"):
            course_id = None
        outcome = learning_service.record_mission_result(
            int(user_id), topic, result, learning_mode=st.session_state.get("learning_mode", ""),
            duration_seconds=_elapsed(), source="mission",
            course_id=course_id,
        )
        _announce(outcome)
    except Exception:
        logger.exception("Could not record the quiz attempt")


def record_homework(result: Mapping[str, Any], topic: str) -> None:
    """Save a submitted homework (dict returned by ``submit_homework``)."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    details = [
        {"correct": d.get("correct"), "concept": d.get("concept", ""), "skill": "Application",
         "q": d.get("question", ""), "chosen": d.get("chosen", ""), "answer": d.get("correct_answer", "")}
        for d in result.get("details", [])
    ]
    try:
        outcome = learning_service.record_quiz_attempt(
            int(user_id), topic, int(result.get("score", 0)), int(result.get("total", 0)),
            duration_seconds=_elapsed(), source="homework", details=details,
        )
        _announce(outcome)
    except Exception:
        logger.exception("Could not record the homework attempt")


def _announce(outcome: Any) -> None:
    """Toast any newly unlocked achievements."""
    for title in getattr(outcome, "new_achievements", ()):
        try:
            st.toast(f"🏆 Achievement unlocked: {title}")
        except Exception:  # nosec B110
            pass
