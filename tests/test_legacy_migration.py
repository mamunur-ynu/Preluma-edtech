"""Dry-run, identity reconciliation, backup and idempotency tests."""

from __future__ import annotations

import csv

from auth import create_user
from database.connection import session_scope
from database.models import HomeworkAssignment, HomeworkSubmission, MigrationQuarantine
from scripts.import_legacy_data import run_import

PW = "Passw0rd!xyz"


def _write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_import_is_dry_run_first_backed_up_and_idempotent(tmp_path):
    create_user("learner", PW, "Unique Learner")
    source = tmp_path / "legacy"
    source.mkdir()
    _write(
        source / "homework.csv",
        ["Homework ID", "Title", "Topic", "Instructions", "Due Date", "Difficulty", "Assigned To",
         "Created By", "Created At", "Published", "Attachment"],
        [{"Homework ID": "H-1", "Title": "Stats", "Topic": "Statistics", "Assigned To": "learner",
          "Published": "true", "Created At": "2026-01-01T00:00:00"}],
    )
    _write(
        source / "homework_submissions.csv",
        ["Submission ID", "Homework ID", "Student", "Score", "Total", "Percentage", "Attempt",
         "Submitted At", "Status"],
        [{"Submission ID": "S-1", "Homework ID": "H-1", "Student": "learner", "Score": "4",
          "Total": "5", "Percentage": "80", "Attempt": "1", "Status": "submitted"}],
    )

    dry = run_import(source)
    assert dry.dry_run and dry.would_insert == {"homework": 1, "submissions": 1}
    with session_scope() as session:
        assert session.query(HomeworkAssignment).count() == 0

    backups = tmp_path / "backups"
    applied = run_import(source, dry_run=False, backup_dir=backups)
    assert applied.inserted == {"homework": 1, "submissions": 1}
    assert (next(backups.iterdir()) / "manifest.json").exists()
    second = run_import(source, dry_run=False, backup_dir=backups)
    assert second.inserted == {}
    assert second.skipped_existing == {"homework": 1, "submissions": 1}
    with session_scope() as session:
        assert session.query(HomeworkAssignment).count() == 1
        assert session.query(HomeworkSubmission).count() == 1


def test_ambiguous_name_is_quarantined_not_guessed(tmp_path):
    create_user("alex-one", PW, "Alex Same")
    create_user("alex-two", PW, "Alex Same")
    source = tmp_path / "legacy"
    source.mkdir()
    _write(
        source / "notifications.csv",
        ["Notification ID", "Student", "Type", "Title", "Message", "Reference ID", "Is Read", "Created At"],
        [{"Notification ID": "N-1", "Student": "Alex Same", "Type": "Announcement", "Title": "Hello"}],
    )
    report = run_import(source, dry_run=False, backup_dir=tmp_path / "backups")
    assert report.quarantined == {"announcements": 1}
    with session_scope() as session:
        rows = session.query(MigrationQuarantine).all()
        assert len(rows) == 1 and "multiple users" in rows[0].reason
