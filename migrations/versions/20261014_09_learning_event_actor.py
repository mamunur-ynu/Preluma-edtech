"""Attribute append-only learning corrections to an operator.

Revision ID: 20261014_09
Revises: 20261014_08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261014_09"
down_revision: Union[str, None] = "20261014_08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("learning_events") as batch_op:
        batch_op.add_column(sa.Column(
            "actor_user_id", sa.Integer(),
            sa.ForeignKey("users.id", name="fk_learning_events_actor_user_id_users", ondelete="RESTRICT"),
            nullable=True,
        ))


def downgrade() -> None:
    corrections = op.get_bind().execute(sa.text(
        "SELECT COUNT(*) FROM learning_events WHERE event_type = 'quiz.voided' "
        "OR actor_user_id IS NOT NULL"
    )).scalar_one()
    if corrections:
        raise RuntimeError("Cannot discard learning correction operator audit")
    with op.batch_alter_table("learning_events") as batch_op:
        batch_op.drop_column("actor_user_id")
