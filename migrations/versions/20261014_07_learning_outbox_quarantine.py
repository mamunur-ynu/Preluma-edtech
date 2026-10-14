"""Retain invalid pending learning events for explicit operator review.

Revision ID: 20261014_07
Revises: 20261013_06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261014_07"
down_revision: Union[str, None] = "20261013_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("learning_outbox", sa.Column("quarantined_at", sa.DateTime(), nullable=True))
    op.add_column("learning_outbox", sa.Column("quarantine_reason", sa.String(32), nullable=True))


def downgrade() -> None:
    quarantined = op.get_bind().execute(sa.text(
        "SELECT COUNT(*) FROM learning_outbox WHERE quarantined_at IS NOT NULL"
    )).scalar_one()
    if quarantined:
        raise RuntimeError("Cannot discard populated learning-event quarantine metadata")
    op.drop_column("learning_outbox", "quarantine_reason")
    op.drop_column("learning_outbox", "quarantined_at")
