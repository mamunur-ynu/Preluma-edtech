"""Shared, database-backed vector chunks.

Revision ID: 20261013_05
Revises: 20261013_04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261013_05"
down_revision: Union[str, None] = "20261013_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vector_chunks",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("doc_id", sa.String(120), nullable=False),
        sa.Column("embedder", sa.String(120), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_vector_chunks_doc_id", "vector_chunks", ["doc_id"])
    op.create_index("ix_vector_chunks_doc_embedder", "vector_chunks", ["doc_id", "embedder"])


def downgrade() -> None:
    op.drop_index("ix_vector_chunks_doc_embedder", table_name="vector_chunks")
    op.drop_index("ix_vector_chunks_doc_id", table_name="vector_chunks")
    op.drop_table("vector_chunks")
