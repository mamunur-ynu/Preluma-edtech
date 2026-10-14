"""Record course provenance for future quiz attempts.

Revision ID: 20261013_02
Revises: 20261013_01

Only legacy attempts with an explicit lesson_id are backfilled. Others remain
unattributed (NULL); current enrollments may have changed since the attempt.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261013_02"
down_revision: Union[str, None] = "20261013_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch:
        batch.add_column(sa.Column("course_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_quiz_attempts_course_id", "courses", ["course_id"], ["id"])
        batch.create_index("ix_quiz_attempts_course_id", ["course_id"])
    # lesson_id, when present, is an unambiguous historical provenance source.
    op.execute(
        "UPDATE quiz_attempts SET course_id = (SELECT course_id FROM lessons "
        "WHERE lessons.id = quiz_attempts.lesson_id) WHERE lesson_id IS NOT NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch:
        batch.drop_index("ix_quiz_attempts_course_id")
        batch.drop_constraint("fk_quiz_attempts_course_id", type_="foreignkey")
        batch.drop_column("course_id")
