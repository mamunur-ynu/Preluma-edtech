"""Transactional quiz evidence and deterministic course-scoped projection.

This sidecar does not change the legacy learning UI. Historical attempts without
unambiguous course provenance are intentionally excluded from course mastery.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from core.learning_engine import QuestionResult
from database.models import CourseMastery, LearningEvent, LearningOutbox, QuizAttempt, User

VOID_REASONS = frozenset({"duplicate_attempt", "assessment_error", "teacher_review"})


@dataclass(frozen=True)
class ProjectionEvidence:
    mastery: float
    attempts: int
    last_event_id: str
    last_practiced_at: datetime
    event_ids: tuple[str, ...]


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
        validated_quiz_payload(session, existing)
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


def validated_quiz_payload(session: Session, event: LearningEvent) -> dict:
    """Reject evidence whose source/provenance or aggregate score has drifted."""
    try:
        source_id = int(event.source_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid quiz source: {event.id}") from exc
    attempt = session.get(QuizAttempt, source_id)
    if (
        attempt is None or event.event_type != "quiz.completed" or event.schema_version != 1
        or event.producer != "learning_service" or event.source_type != "quiz_attempt"
        or event.idempotency_key != f"quiz:{source_id}"
        or event.actor_user_id is not None
        or event.user_id != attempt.user_id or event.course_id != attempt.course_id
        or event.lesson_id != attempt.lesson_id or event.occurred_at != attempt.created_at
    ):
        raise ValueError(f"Quiz evidence provenance mismatch: {event.id}")
    try:
        payload = json.loads(event.payload_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid quiz evidence payload: {event.id}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid quiz evidence payload: {event.id}")
    score, total, percentage = payload.get("score"), payload.get("total"), payload.get("percentage")
    if (
        payload.get("topic") != attempt.topic or not isinstance(attempt.topic, str)
        or not attempt.topic or len(attempt.topic) > 80
        or type(score) is not int or score != attempt.score
        or type(total) is not int or total != attempt.total or total <= 0
        or type(percentage) not in (int, float)
        or not math.isfinite(percentage)
        or not math.isclose(percentage, attempt.percentage, abs_tol=1e-9)
        or not 0 <= percentage <= 100
    ):
        raise ValueError(f"Quiz evidence score mismatch: {event.id}")
    concepts = payload.get("concepts", [])
    if not isinstance(concepts, list):
        raise ValueError(f"Invalid concept evidence: {event.id}")
    seen: set[str] = set()
    for item in concepts:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid concept evidence: {event.id}")
        concept, correct, count = item.get("concept"), item.get("score"), item.get("total")
        if (
            not isinstance(concept, str) or not concept or len(concept) > 80 or concept in seen
            or type(correct) is not int or type(count) is not int
            or count <= 0 or not 0 <= correct <= count
        ):
            raise ValueError(f"Invalid concept evidence: {event.id}")
        seen.add(concept)
    return payload


def validated_void_payload(session: Session, event: LearningEvent) -> LearningEvent:
    """Validate a one-way correction and its still-verifiable source evidence."""
    original = session.get(LearningEvent, event.source_id)
    actor = session.get(User, event.actor_user_id) if event.actor_user_id is not None else None
    if (
        original is None or original.id == event.id or actor is None
        or event.event_type != "quiz.voided" or event.schema_version != 1
        or event.producer != "learning_correction" or event.source_type != "learning_event"
        or event.idempotency_key != f"void:{original.id}"
        or original.event_type != "quiz.completed" or original.course_id is None
        or event.user_id != original.user_id or event.course_id != original.course_id
        or event.lesson_id != original.lesson_id
        or event.occurred_at < original.recorded_at
    ):
        raise ValueError(f"Invalid learning correction provenance: {event.id}")
    validated_quiz_payload(session, original)
    try:
        payload = json.loads(event.payload_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid learning correction payload: {event.id}") from exc
    if (
        not isinstance(payload, dict) or set(payload) != {"original_event_id", "reason_code"}
        or payload.get("original_event_id") != original.id
        or not isinstance(payload.get("reason_code"), str)
        or payload["reason_code"] not in VOID_REASONS
    ):
        raise ValueError(f"Invalid learning correction payload: {event.id}")
    return original


def expected_course_mastery(
    session: Session, user_id: int, course_id: int,
) -> dict[tuple[str, str], ProjectionEvidence]:
    """Compute the complete course projection without writing it."""
    events = session.scalars(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.course_id == course_id,
        ).order_by(LearningEvent.occurred_at, LearningEvent.id)
    ).all()
    quiz_events: list[tuple[LearningEvent, dict]] = []
    voided_ids: set[str] = set()
    for event in events:
        if event.event_type == "quiz.completed":
            quiz_events.append((event, validated_quiz_payload(session, event)))
        elif event.event_type == "quiz.voided":
            original = validated_void_payload(session, event)
            if original.id in voided_ids:
                raise ValueError(f"Duplicate learning correction: {event.id}")
            voided_ids.add(original.id)
        else:
            raise ValueError(f"Unsupported learning event: {event.id}")
    by_key: dict[tuple[str, str], list[tuple[LearningEvent, float]]] = defaultdict(list)
    for event, payload in quiz_events:
        if event.id in voided_ids:
            continue
        topic = payload["topic"]
        percentage = float(payload["percentage"])
        by_key[(topic, "")].append((event, percentage))
        for item in payload.get("concepts", []):
            concept = item["concept"]
            score, total = int(item["score"]), int(item["total"])
            by_key[(topic, concept)].append((event, 100.0 * score / total))

    expected = {}
    for key, evidence in sorted(by_key.items()):
        latest = evidence[-3:]
        weights = list(range(1, len(latest) + 1))
        mastery = round(sum(score * weight for (_, score), weight in zip(latest, weights)) / sum(weights), 1)
        last = evidence[-1][0]
        expected[key] = ProjectionEvidence(
            mastery, len(evidence), last.id, last.occurred_at,
            tuple(event.id for event, _ in evidence),
        )
    return expected


def rebuild_course_mastery(session: Session, user_id: int, course_id: int) -> list[CourseMastery]:
    """Replay only attributed events for one user/course; latest 3 weighted 3:2:1."""
    # Serialize concurrent PostgreSQL replays for this exact learner/course pair.
    # SQLite is used only for single-process local demos and synthetic tests.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:user_id, :course_id)"),
            {"user_id": user_id, "course_id": course_id},
        )
    expected = expected_course_mastery(session, user_id, course_id)
    # Replacing only this course's projection makes retries and late events deterministic.
    session.execute(delete(CourseMastery).where(
        CourseMastery.user_id == user_id, CourseMastery.course_id == course_id,
    ))
    rows = []
    for (topic, concept), item in expected.items():
        row = CourseMastery(
            user_id=user_id, course_id=course_id, topic=topic, concept=concept,
            mastery=item.mastery, attempts=item.attempts, last_event_id=item.last_event_id,
            last_practiced_at=item.last_practiced_at, projection_version=1,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows
