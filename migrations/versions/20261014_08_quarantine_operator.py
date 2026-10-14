"""Record an authorized quarantine operator without guessing legacy actors.

Revision ID: 20261014_08
Revises: 20261014_07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261014_08"
down_revision: Union[str, None] = "20261014_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("learning_outbox") as batch_op:
        batch_op.add_column(sa.Column(
            "quarantined_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", name="fk_learning_outbox_quarantined_by_user_id_users", ondelete="RESTRICT"),
            nullable=True,
        ))


def downgrade() -> None:
    attributed = op.get_bind().execute(sa.text(
        "SELECT COUNT(*) FROM learning_outbox WHERE quarantined_by_user_id IS NOT NULL"
    )).scalar_one()
    if attributed:
        raise RuntimeError("Cannot discard learning-event quarantine operator audit")
    with op.batch_alter_table("learning_outbox") as batch_op:
        batch_op.drop_column("quarantined_by_user_id")
