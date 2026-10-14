"""Opt-in, admin-authorized correction of shadow course evidence only.

No browser/API route calls this module. The original attempt and event remain
untouched; legacy global mastery is intentionally not recalculated here.
"""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database.connection import session_scope
from database.models import LearningEvent, LearningOutbox, utcnow
from services.learning_events import (
    VOID_REASONS, rebuild_course_mastery, validated_quiz_payload, validated_void_payload,
)
from services.learning_outbox import require_live_learning_admin


def voided_attempt_ids(
    session: Session, user_ids: set[int], course_ids: set[int] | None = None,
) -> set[int]:
    """Validate relevant corrections before excluding source attempts from quiz metrics.

    Looking up corrections by either their claimed learner or source learner
    ensures a corrupted correction cannot silently restore a voided attempt.
    """
    if not user_ids or course_ids == set():
        return set()
    source_ids = select(LearningEvent.id).where(
        LearningEvent.event_type == "quiz.completed", LearningEvent.user_id.in_(user_ids),
    )
    if course_ids is not None:
        source_ids = source_ids.where(LearningEvent.course_id.in_(course_ids))
    claimed_scope = LearningEvent.user_id.in_(user_ids)
    if course_ids is not None:
        claimed_scope = claimed_scope & LearningEvent.course_id.in_(course_ids)
    corrections = session.scalars(select(LearningEvent).where(
        or_(LearningEvent.event_type == "quiz.voided", LearningEvent.producer == "learning_correction"),
        or_(claimed_scope, LearningEvent.source_id.in_(source_ids)),
    )).all()
    result: set[int] = set()
    for correction in corrections:
        original = validated_void_payload(session, correction)
        if original.user_id in user_ids and (
            course_ids is None or original.course_id in course_ids
        ):
            attempt_id = int(original.source_id)
            if attempt_id in result:
                raise ValueError("Duplicate learning correction")
            result.add(attempt_id)
    return result


def void_quiz_evidence(event_id: str, operator_session: str, reason_code: str) -> str:
    """Append one compensating event and rebuild its course in one transaction.

    Only a source-valid, course-attributed quiz may be voided. Corrupt evidence
    belongs in quarantine/manual review, not in an invented course correction.
    """
    if not isinstance(reason_code, str) or reason_code not in VOID_REASONS:
        raise ValueError("Unsupported correction reason")
    if not isinstance(event_id, str) or len(event_id) > 36:
        raise ValueError("Invalid learning event ID")
    with session_scope() as session:
        operator = require_live_learning_admin(session, operator_session)
        original = session.scalar(select(LearningEvent).where(
            LearningEvent.id == event_id,
        ).with_for_update())
        if original is None or original.event_type != "quiz.completed" or original.course_id is None:
            raise ValueError("Attributed quiz evidence required")
        validated_quiz_payload(session, original)
        marker = session.get(LearningOutbox, original.id)
        if marker is None or marker.quarantined_at is not None:
            raise ValueError("Quarantined or untracked evidence cannot be corrected")
        existing = session.scalar(select(LearningEvent).where(
            LearningEvent.producer == "learning_correction",
            LearningEvent.idempotency_key == f"void:{original.id}",
        ))
        if existing is not None:
            validated_void_payload(session, existing)
            if json.loads(existing.payload_json)["reason_code"] != reason_code:
                raise ValueError("Correction reason differs from existing decision")
            return existing.id
        now = utcnow()
        event = LearningEvent(
            id=str(uuid4()), schema_version=1, event_type="quiz.voided",
            user_id=original.user_id, course_id=original.course_id,
            lesson_id=original.lesson_id, source_type="learning_event",
            source_id=original.id, producer="learning_correction",
            idempotency_key=f"void:{original.id}", actor_user_id=operator.id,
            occurred_at=now, recorded_at=now,
            payload_json=json.dumps({
                "original_event_id": original.id, "reason_code": reason_code,
            }, separators=(",", ":"), sort_keys=True),
        )
        session.add(event)
        session.add(LearningOutbox(event_id=event.id))
        session.flush()
        rebuild_course_mastery(session, original.user_id, original.course_id)
        return event.id
