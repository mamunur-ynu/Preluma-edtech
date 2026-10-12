"""Repositories for the incremental CSV-to-relational migration target."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    Announcement,
    HomeworkAssignment,
    HomeworkSubmission,
    LearningProject,
    MigrationQuarantine,
    ProjectFile,
)


class LegacyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def homework_by_legacy_id(self, legacy_id: str) -> HomeworkAssignment | None:
        return self.session.scalar(select(HomeworkAssignment).where(HomeworkAssignment.legacy_id == legacy_id))

    def add_homework(self, row: HomeworkAssignment) -> HomeworkAssignment:
        self.session.add(row)
        self.session.flush()
        return row

    def submission_by_legacy_id(self, legacy_id: str) -> HomeworkSubmission | None:
        return self.session.scalar(select(HomeworkSubmission).where(HomeworkSubmission.legacy_id == legacy_id))

    def add_submission(self, row: HomeworkSubmission) -> HomeworkSubmission:
        self.session.add(row)
        self.session.flush()
        return row

    def project_by_legacy_id(self, legacy_id: str) -> LearningProject | None:
        return self.session.scalar(select(LearningProject).where(LearningProject.legacy_id == legacy_id))

    def add_project(self, row: LearningProject) -> LearningProject:
        self.session.add(row)
        self.session.flush()
        return row

    def file_by_legacy_id(self, legacy_id: str) -> ProjectFile | None:
        return self.session.scalar(select(ProjectFile).where(ProjectFile.legacy_id == legacy_id))

    def add_file(self, row: ProjectFile) -> ProjectFile:
        self.session.add(row)
        self.session.flush()
        return row

    def announcement_by_legacy_id(self, legacy_id: str) -> Announcement | None:
        return self.session.scalar(select(Announcement).where(Announcement.legacy_id == legacy_id))

    def add_announcement(self, row: Announcement) -> Announcement:
        self.session.add(row)
        self.session.flush()
        return row

    def add_quarantine(self, row: MigrationQuarantine) -> None:
        exists = self.session.scalar(
            select(MigrationQuarantine).where(
                MigrationQuarantine.source_name == row.source_name,
                MigrationQuarantine.row_number == row.row_number,
                MigrationQuarantine.payload_sha256 == row.payload_sha256,
            )
        )
        if exists is None:
            self.session.add(row)
            self.session.flush()
