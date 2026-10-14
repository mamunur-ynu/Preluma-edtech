"""Opt-in local outbox replay; no scheduler or external publisher is enabled."""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from config import get_settings
from database.connection import session_scope
from database.models import ROLE_ADMIN, LearningEvent, LearningOutbox, User, UserSession, utcnow
from services.learning_events import (
    rebuild_course_mastery, validated_quiz_payload, validated_void_payload,
)


def require_live_learning_admin(session, operator_session: str) -> User:
    """Resolve a live administrator inside the caller's transaction."""
    if not isinstance(operator_session, str) or not operator_session or len(operator_session) > 200:
        raise PermissionError("Active administrator session required")
    token_hash = hashlib.sha256(operator_session.encode("utf-8")).hexdigest()
    identity = session.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > utcnow(),
        ).with_for_update()
    )
    operator = session.scalar(
        select(User).where(User.id == identity.user_id).with_for_update()
    ) if identity is not None else None
    if (operator is None or not operator.is_active or (
        operator.role != ROLE_ADMIN
        and operator.username not in get_settings().admin_usernames
    )):
        raise PermissionError("Active administrator session required")
    return operator


def validate_supported_learning_event(session, event: LearningEvent) -> None:
    if event.schema_version != 1:
        raise ValueError(f"Unsupported learning event: {event.id}")
    if event.event_type == "quiz.completed":
        validated_quiz_payload(session, event)
    elif event.event_type == "quiz.voided":
        validated_void_payload(session, event)
    else:
        raise ValueError(f"Unsupported learning event: {event.id}")


def process_next_learning_event() -> str | None:
    """Replay one pending event and acknowledge it in the same transaction.

    PostgreSQL row locks allow competing callers to skip a claimed row. SQLite
    ignores ``FOR UPDATE`` and is supported only for single-process demos.
    A failure rolls back both the projection and delivery marker for retry.
    """
    with session_scope() as session:
        pending = session.scalar(
            select(LearningOutbox)
            .where(
                LearningOutbox.delivered_at.is_(None),
                LearningOutbox.quarantined_at.is_(None),
            )
            .order_by(LearningOutbox.created_at, LearningOutbox.event_id)
            .limit(1)
            .with_for_update(of=LearningOutbox, skip_locked=True)
        )
        if pending is None:
            return None
        event = session.get(LearningEvent, pending.event_id)
        if event is None:  # FK integrity should make this unreachable.
            raise ValueError(f"Outbox event is missing: {pending.event_id}")
        # Ambiguous (course-less) evidence must also pass provenance validation.
        validate_supported_learning_event(session, event)
        if event.course_id is not None:
            rebuild_course_mastery(session, event.user_id, event.course_id)
        pending.delivered_at = utcnow()
        return event.id


def quarantine_invalid_learning_event(event_id: str, operator_session: str) -> bool:
    """Explicitly isolate one deterministically invalid pending event.

    A live administrator session is required; the operator is recorded with
    the marker. This action never repairs or discards evidence. Database and
    network errors still raise for retry; a valid event cannot be quarantined.
    Other events for the same course continue to fail closed during rebuild.
    """
    with session_scope() as session:
        operator = require_live_learning_admin(session, operator_session)
        pending = session.scalar(
            select(LearningOutbox)
            .where(LearningOutbox.event_id == event_id)
            .with_for_update(of=LearningOutbox)
        )
        if pending is None or pending.delivered_at is not None:
            return False
        if pending.quarantined_at is not None:
            return True
        event = session.get(LearningEvent, event_id)
        if event is None:
            raise ValueError("Missing learning event cannot be classified")
        try:
            validate_supported_learning_event(session, event)
        except ValueError:
            reason = "unsupported_schema" if event.schema_version != 1 or event.event_type not in (
                "quiz.completed", "quiz.voided",
            ) else "invalid_evidence"
        else:
            return False
        pending.quarantined_at = utcnow()
        pending.quarantine_reason = reason
        pending.quarantined_by_user_id = operator.id
        return True
