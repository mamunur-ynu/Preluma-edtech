"""Retain encrypted uploaded source text for interrupted-index recovery.

Revision ID: 20261013_03
Revises: 20261013_02

Existing documents have no recoverable source until their owner re-uploads.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261013_03"
down_revision: Union[str, None] = "20261013_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.add_column(sa.Column("source_ciphertext", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_column("source_ciphertext")
