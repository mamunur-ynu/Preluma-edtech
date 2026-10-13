"""Transactional quiz evidence and deterministic course-scoped projection.

This sidecar does not change the legacy learning UI. Historical attempts without
unambiguous course provenance are intentionally excluded from course mastery.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from core.learning_engine import QuestionResult
from database.models import CourseMastery, LearningEvent, LearningOutbox, QuizAttempt


def append_quiz_event(
    session: Session, attempt: QuizAttempt, results: Sequence[QuestionResult] = (),
) -> LearningEvent:
    """Append minimal aggregate evidence and outbox row in the attempt's transaction."""
    if attempt.id is None:
        session.flush()
    key = f"quiz:{attempt.id}"
    existing = session.scalar(
        select(LearningEvent).where(
            LearningEvent.producer == "learning_service",
            LearningEvent.idempotency_key == key,
        )
    )
    if existing is not None:
        return existing
    concepts: dict[str, list[bool]] = defaultdict(list)
    for result in results:
        concept = result.concept.strip()
        if concept and len(concept) <= 80:
            concepts[concept].append(result.correct)
    aggregates = [
        {"concept": concept, "score": sum(outcomes), "total": len(outcomes)}
        for concept, outcomes in sorted(concepts.items())
    ]
    event = LearningEvent(
        id=str(uuid4()), schema_version=1, event_type="quiz.completed",
        user_id=attempt.user_id, course_id=attempt.course_id, lesson_id=attempt.lesson_id,
        source_type="quiz_attempt", source_id=str(attempt.id),
        producer="learning_service", idempotency_key=key,
        occurred_at=attempt.created_at,
        payload_json=json.dumps({
            "topic": attempt.topic, "score": attempt.score,
            "total": attempt.total, "percentage": attempt.percentage,
            "concepts": aggregates,
        }, separators=(",", ":"), sort_keys=True),
    )
    session.add(event)
    session.add(LearningOutbox(event_id=event.id))
    session.flush()
    return event


def rebuild_course_mastery(session: Session, user_id: int, course_id: int) -> list[CourseMastery]:
    """Replay only attributed events for one user/course; latest 3 weighted 3:2:1."""
    # Serialize concurrent PostgreSQL replays for this exact learner/course pair.
    # SQLite is used only for single-process local demos and synthetic tests.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:user_id, :course_id)"),
            {"user_id": user_id, "course_id": course_id},
        )
    events = session.scalars(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.course_id == course_id,
            LearningEvent.event_type == "quiz.completed",
            LearningEvent.schema_version == 1,
        ).order_by(LearningEvent.occurred_at, LearningEvent.id)
    ).all()
    by_key: dict[tuple[str, str], list[tuple[LearningEvent, float]]] = defaultdict(list)
    for event in events:
        payload = json.loads(event.payload_json)
        topic = payload["topic"]
        percentage = float(payload["percentage"])
        if not isinstance(topic, str) or not topic or not 0 <= percentage <= 100:
            raise ValueError(f"Invalid learning event: {event.id}")
        by_key[(topic, "")].append((event, percentage))
        for item in payload.get("concepts", []):
            concept = item["concept"]
            score, total = int(item["score"]), int(item["total"])
            if not isinstance(concept, str) or not concept or len(concept) > 80 or not 0 <= score <= total or total == 0:
                raise ValueError(f"Invalid concept evidence: {event.id}")
            by_key[(topic, concept)].append((event, 100.0 * score / total))

    # Replacing only this course's projection makes retries and late events deterministic.
    session.execute(delete(CourseMastery).where(
        CourseMastery.user_id == user_id, CourseMastery.course_id == course_id,
    ))
    rows = []
    for (topic, concept), evidence in sorted(by_key.items()):
        latest = evidence[-3:]
        weights = list(range(1, len(latest) + 1))
        mastery = round(sum(score * weight for (_, score), weight in zip(latest, weights)) / sum(weights), 1)
        last = evidence[-1][0]
        row = CourseMastery(
            user_id=user_id, course_id=course_id, topic=topic, concept=concept,
            mastery=mastery, attempts=len(evidence), last_event_id=last.id,
            last_practiced_at=last.occurred_at, projection_version=1,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows
