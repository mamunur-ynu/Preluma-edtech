"""Explainable, course-scoped shadow recommendations (no UI or persistence cutover)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

from database.connection import session_scope
from database.models import Course, CourseMastery, LearningEvent, Lesson
from database.repository import EnrollmentRepository
from services._access import require_active_user
from services._common import now_utc

RULE_VERSION = 1
READY_SCORE = 80.0
PRACTICE_SCORE = 70.0
STALE_DAYS = 14


@dataclass(frozen=True)
class CourseRecommendation:
    course_id: int
    lesson_id: int | None
    rule_id: str
    rule_version: int
    topic: str | None
    title: str
    reason: str
    score: float | None
    attempts: int
    evidence_event_ids: tuple[str, ...]


def _evidence_map(session, user_id: int, course_id: int) -> dict[str, tuple[str, ...]]:
    events = session.scalars(select(LearningEvent).where(
        LearningEvent.user_id == user_id,
        LearningEvent.course_id == course_id,
        LearningEvent.event_type == "quiz.completed",
        LearningEvent.schema_version == 1,
    ).order_by(LearningEvent.occurred_at, LearningEvent.id)).all()
    by_topic: dict[str, list[str]] = {}
    for event in events:
        by_topic.setdefault(json.loads(event.payload_json)["topic"], []).append(event.id)
    return {topic: tuple(ids[-3:]) for topic, ids in by_topic.items()}


def get_course_recommendation(
    user_id: int, course_id: int, *, now: datetime | None = None,
) -> CourseRecommendation:
    """Return one deterministic next step; only an active enrollee may request it."""
    current = now or now_utc()
    with session_scope() as session:
        require_active_user(session, user_id)
        course = session.get(Course, course_id)
        if course is None or not EnrollmentRepository(session).is_enrolled(user_id, course_id):
            raise PermissionError("An enrolled course is required.")
        lessons = session.scalars(select(Lesson).where(
            Lesson.course_id == course_id,
        ).order_by(Lesson.order_index, Lesson.id)).all()
        if not lessons:
            return CourseRecommendation(
                course_id, None, "empty_course", RULE_VERSION, None,
                f"{course.title} has no lessons", "Ask your teacher to add a lesson.",
                None, 0, (),
            )
        rows = session.scalars(select(CourseMastery).where(
            CourseMastery.user_id == user_id,
            CourseMastery.course_id == course_id,
            CourseMastery.concept == "",
        )).all()
        mastery = {row.topic: row for row in rows}
        evidence_by_topic = _evidence_map(session, user_id, course_id)
        for lesson in lessons:
            row = mastery.get(lesson.topic_key)
            evidence_ids = evidence_by_topic.get(lesson.topic_key, ())
            if row is None:
                return CourseRecommendation(
                    course_id, lesson.id, "cold_start", RULE_VERSION, lesson.topic_key,
                    f"Start {lesson.title}",
                    f"No attributed quiz evidence for {lesson.title} in {course.title} yet.",
                    None, 0, (),
                )
            if row.attempts >= 2 and row.mastery >= READY_SCORE:
                continue
            if row.attempts < 2:
                rule_id = "provisional_practice"
                reason = (
                    f"{lesson.title} has {row.attempts} attributed quiz attempt(s) in {course.title}; "
                    "at least two are needed before moving on."
                )
            elif row.mastery < PRACTICE_SCORE:
                rule_id = "practice"
                reason = (
                    f"{lesson.title} is at {row.mastery:.1f}% from {row.attempts} attributed "
                    f"attempts in {course.title}; practise before moving on."
                )
            elif current - row.last_practiced_at > timedelta(days=STALE_DAYS):
                rule_id = "review"
                reason = (
                    f"{lesson.title} was last practised on {row.last_practiced_at.date().isoformat()} "
                    f"and is at {row.mastery:.1f}% in {course.title}; review it."
                )
            else:
                rule_id = "practice"
                reason = (
                    f"{lesson.title} is at {row.mastery:.1f}% in {course.title}; "
                    f"reach {READY_SCORE:.0f}% across at least two attempts before moving on."
                )
            return CourseRecommendation(
                course_id, lesson.id, rule_id, RULE_VERSION, lesson.topic_key,
                f"Practise {lesson.title}" if rule_id != "review" else f"Review {lesson.title}",
                reason, row.mastery, row.attempts, evidence_ids,
            )
        return CourseRecommendation(
            course_id, None, "course_ready", RULE_VERSION, None,
            f"{course.title} is ready", "Every lesson has at least two attributed attempts and an 80% score.",
            None, 0, (),
        )
