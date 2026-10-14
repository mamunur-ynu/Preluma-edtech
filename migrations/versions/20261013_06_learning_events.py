"""Course-scoped learning evidence and rebuildable mastery projection.

Revision ID: 20261013_06
Revises: 20261013_05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261013_06"
down_revision: Union[str, None] = "20261013_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("producer", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("producer", "idempotency_key", name="uq_learning_event_producer_key"),
    )
    op.create_index(
        "ix_learning_event_course_replay", "learning_events",
        ["user_id", "course_id", "occurred_at", "id"],
    )
    op.create_table(
        "learning_outbox",
        sa.Column("event_id", sa.String(36), sa.ForeignKey("learning_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "course_mastery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(80), nullable=False),
        sa.Column("concept", sa.String(80), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_event_id", sa.String(36), nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(), nullable=False),
        sa.Column("projection_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "course_id", "topic", "concept", name="uq_course_mastery"),
    )
    op.create_index("ix_course_mastery_user_id", "course_mastery", ["user_id"])
    op.create_index("ix_course_mastery_course_id", "course_mastery", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_course_mastery_course_id", table_name="course_mastery")
    op.drop_index("ix_course_mastery_user_id", table_name="course_mastery")
    op.drop_table("course_mastery")
    op.drop_table("learning_outbox")
    op.drop_index("ix_learning_event_course_replay", table_name="learning_events")
    op.drop_table("learning_events")
