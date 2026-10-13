"""Opt-in local outbox replay; no scheduler or external publisher is enabled."""

from __future__ import annotations

from sqlalchemy import select

from database.connection import session_scope
from database.models import LearningEvent, LearningOutbox, utcnow
from services.learning_events import rebuild_course_mastery


def process_next_learning_event() -> str | None:
    """Replay one pending event and acknowledge it in the same transaction.

    PostgreSQL row locks allow competing callers to skip a claimed row. SQLite
    ignores ``FOR UPDATE`` and is supported only for single-process demos.
    A failure rolls back both the projection and delivery marker for retry.
    """
    with session_scope() as session:
        pending = session.scalar(
            select(LearningOutbox)
            .where(LearningOutbox.delivered_at.is_(None))
            .order_by(LearningOutbox.created_at, LearningOutbox.event_id)
            .limit(1)
            .with_for_update(of=LearningOutbox, skip_locked=True)
        )
        if pending is None:
            return None
        event = session.get(LearningEvent, pending.event_id)
        if event is None:  # FK integrity should make this unreachable.
            raise ValueError(f"Outbox event is missing: {pending.event_id}")
        if event.event_type != "quiz.completed" or event.schema_version != 1:
            raise ValueError(f"Unsupported learning event: {event.id}")
        if event.course_id is not None:
            rebuild_course_mastery(session, event.user_id, event.course_id)
        pending.delivered_at = utcnow()
        return event.id
