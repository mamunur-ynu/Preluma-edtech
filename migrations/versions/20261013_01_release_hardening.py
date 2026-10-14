"""Add release-hardening relational targets and RAG provenance.

Revision ID: 20261013_01
Revises: None
Create Date: 2026-10-13

This is the reviewed baseline migration for existing v5.1 databases. Clean
local installs may still use Base.metadata.create_all; staged deployments
should back up, stamp this baseline only after inspection, then upgrade.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261013_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.add_column(sa.Column("visibility", sa.String(16), nullable=False, server_default="public"))
        batch.add_column(sa.Column("content_sha256", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_index("ix_knowledge_documents_visibility", ["visibility"])
        batch.create_index("ix_knowledge_documents_content_sha256", ["content_sha256"])

    op.create_table(
        "homework_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.String(80), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("topic", sa.String(120), nullable=False, server_default=""),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_text", sa.String(120), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(32), nullable=False, server_default=""),
        sa.Column("assigned_to_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("attachment_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("legacy_id"),
    )
    op.create_index("ix_homework_assignments_legacy_id", "homework_assignments", ["legacy_id"], unique=True)
    op.create_index("ix_homework_assignments_created_by_id", "homework_assignments", ["created_by_id"])
    op.create_index("ix_homework_assignments_is_published", "homework_assignments", ["is_published"])

    op.create_table(
        "homework_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.String(80), nullable=False, unique=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("homework_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="submitted"),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("assignment_id", "student_id", "attempt", name="uq_homework_attempt"),
    )
    op.create_index("ix_homework_submissions_legacy_id", "homework_submissions", ["legacy_id"], unique=True)
    op.create_index("ix_homework_submissions_assignment_id", "homework_submissions", ["assignment_id"])
    op.create_index("ix_homework_submissions_student_id", "homework_submissions", ["student_id"])

    op.create_table(
        "learning_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_text", sa.String(120), nullable=False, server_default=""),
        sa.Column("project_type", sa.String(20), nullable=False, server_default="class"),
        sa.Column("status", sa.String(24), nullable=False, server_default="In Progress"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, cols, unique in (
        ("ix_learning_projects_legacy_id", ["legacy_id"], True),
        ("ix_learning_projects_project_type", ["project_type"], False),
        ("ix_learning_projects_status", ["status"], False),
        ("ix_learning_projects_is_published", ["is_published"], False),
        ("ix_learning_projects_created_by_id", ["created_by_id"], False),
        ("ix_learning_projects_owner_id", ["owner_id"], False),
    ):
        op.create_index(name, "learning_projects", cols, unique=unique)

    op.create_table(
        "project_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.String(80), nullable=False, unique=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("learning_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("filename", sa.String(180), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(120), nullable=False, server_default=""),
        sa.Column("content_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_project_files_legacy_id", "project_files", ["legacy_id"], unique=True)
    op.create_index("ix_project_files_project_id", "project_files", ["project_id"])
    op.create_index("ix_project_files_uploaded_by_id", "project_files", ["uploaded_by_id"])

    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("audience_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_announcements_legacy_id", "announcements", ["legacy_id"], unique=True)
    op.create_index("ix_announcements_created_by_id", "announcements", ["created_by_id"])

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("extras_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("avatar_object_key", sa.String(500), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "legacy_import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="started"),
        sa.Column("counts_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_legacy_import_runs_source_name", "legacy_import_runs", ["source_name"])
    op.create_index("ix_legacy_import_runs_source_sha256", "legacy_import_runs", ["source_sha256"])

    op.create_table(
        "migration_quarantine",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_name", "row_number", "payload_sha256", name="uq_quarantine_row"),
    )
    op.create_index("ix_migration_quarantine_source_name", "migration_quarantine", ["source_name"])


def downgrade() -> None:
    for table in (
        "migration_quarantine",
        "legacy_import_runs",
        "user_profiles",
        "announcements",
        "project_files",
        "learning_projects",
        "homework_submissions",
        "homework_assignments",
    ):
        op.drop_table(table)
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_index("ix_knowledge_documents_content_sha256")
        batch.drop_index("ix_knowledge_documents_visibility")
        batch.drop_column("version")
        batch.drop_column("content_sha256")
        batch.drop_column("visibility")
