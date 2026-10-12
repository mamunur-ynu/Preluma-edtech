"""
services/recommendation_service.py — the personal learning path, as a use case.

::

    plan = recommendation_service.get_plan(user_id)       # what the UI calls
    for step in plan.steps: ...                           # step.title, step.reason, step.kind

The *decision* is made by the explainable rule engine in ``core.recommendation_engine``.
When an LLM is configured the plan also gets a short, motivating ``coach_note``; if the model
is unavailable the plan is identical minus that sentence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.knowledge_graph import build_graph
from core.recommendation_engine import PathStep, build_learning_path
from database.connection import session_scope
from database.models import Recommendation
from database.repository import RecommendationRepository
from services import course_service, learning_service
from services._common import now_utc, title_for

logger = logging.getLogger("preluma.recommendations")


@dataclass(frozen=True)
class PlanStep:
    id: int | None
    order: int
    kind: str
    topic: str
    topic_title: str
    concept: str
    title: str
    reason: str
    estimated_minutes: int
    priority_label: str


@dataclass(frozen=True)
class LearningPlan:
    steps: list[PlanStep]
    summary: str
    coach_note: str = ""

    @property
    def total_minutes(self) -> int:
        return sum(step.estimated_minutes for step in self.steps)


def _summary(steps: list[PathStep], overall: float, has_data: bool) -> str:
    if not has_data:
        return "Take your first quiz and Preluma will build a path around what you find hard."
    revise = sum(1 for s in steps if s.kind == "revise")
    if revise:
        return f"{revise} topic{'s' if revise != 1 else ''} need attention first, then you can move on. Overall mastery: {overall:.0f}%."
    return f"You're on track (overall mastery {overall:.0f}%). Keep practising and unlock the next topics."


def get_plan(user_id: int, *, max_steps: int = 5, with_ai_note: bool = False, persist: bool = True) -> LearningPlan:
    """Build (and optionally store) the student's current learning path."""
    profile = learning_service.get_profile(user_id)
    snap = learning_service.get_snapshot(user_id)
    focus = course_service.enrolled_topic_keys(user_id) or None
    steps = build_learning_path(profile, build_graph(), now=now_utc(), max_steps=max_steps, focus_topics=focus)

    stored_ids: list[int | None] = [None] * len(steps)
    if persist:
        with session_scope() as s:
            repo = RecommendationRepository(s)
            current = [(r.kind, r.topic, r.concept) for r in repo.active_for_user(user_id)]
            wanted = [(st.kind, st.topic, st.concept) for st in steps]
            if current != wanted:                       # only rewrite when the path really changed
                rows = repo.replace_active(user_id, [
                    Recommendation(kind=st.kind, topic=st.topic, concept=st.concept, title=st.title[:160],
                                   reason=st.reason, priority=i)
                    for i, st in enumerate(steps, start=1)
                ])
                stored_ids = [r.id for r in rows]
            else:
                stored_ids = [r.id for r in repo.active_for_user(user_id)]

    plan_steps = [
        PlanStep(stored_ids[i], i + 1, st.kind, st.topic, title_for(st.topic), st.concept, st.title, st.reason,
                 st.estimated_minutes, st.priority_label)
        for i, st in enumerate(steps)
    ]
    plan = LearningPlan(plan_steps, _summary(steps, snap.overall_mastery, bool(snap.topic_mastery)))
    if with_ai_note and plan_steps:
        note = _coach_note(plan)
        if note:
            plan = LearningPlan(plan.steps, plan.summary, note)
    return plan


def _coach_note(plan: LearningPlan) -> str:
    """One or two motivating sentences from the LLM (empty string if unavailable)."""
    try:
        from services import ai_service

        if not ai_service.llm_available():
            return ""
        steps = "; ".join(f"{s.order}. {s.title} ({s.reason})" for s in plan.steps[:4])
        return ai_service.complete_text(
            "You are a warm study coach. Reply in at most two short sentences, no lists, no markdown.",
            f"A student's learning plan is: {steps}. Encourage them and say which step to start with and why.",
        )
    except Exception as exc:
        logger.info("Coach note unavailable: %s", exc)
        return ""


def mark_step(user_id: int, recommendation_id: int, status: str) -> bool:
    """Mark a stored step ``done`` or ``dismissed``."""
    if status not in ("done", "dismissed"):
        raise ValueError("status must be 'done' or 'dismissed'")
    with session_scope() as s:
        return RecommendationRepository(s).set_status(recommendation_id, user_id, status)
