#!/usr/bin/env python3
"""Dry-run-first, idempotent import of legacy Preluma CSV stores.

Examples:
    python scripts/import_legacy_data.py --source-dir data
    python scripts/import_legacy_data.py --source-dir /safe/copy --apply --backup-dir /safe/backups

Dry-run is the default. Applying requires the explicit ``--apply`` flag. Identity
resolution prefers usernames; a full name is accepted only when it uniquely maps
to one account. Ambiguous or missing relationships are quarantined, never guessed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import session_scope  # noqa: E402
from database.legacy_repository import LegacyRepository  # noqa: E402
from database.models import (  # noqa: E402
    Announcement,
    HomeworkAssignment,
    HomeworkSubmission,
    LearningProject,
    MigrationQuarantine,
    ProjectFile,
    User,
    utcnow,
)
from database.repository import UserRepository  # noqa: E402


@dataclass
class ImportReport:
    dry_run: bool
    source_dir: str
    source_hashes: dict[str, str]
    rows_seen: dict[str, int]
    would_insert: dict[str, int]
    inserted: dict[str, int]
    skipped_existing: dict[str, int]
    quarantined: dict[str, int]
    unresolved_optional_identities: dict[str, int]
    backup_dir: str = ""


def _read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _truthy(value: str) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "published", "complete"}


def _number(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: str, default: int = 1) -> int:
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default


def _date(value: str) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    if raw:
        try:
            parsed = datetime.fromisoformat(raw)
            return parsed.replace(tzinfo=None)
        except ValueError:
            pass
    return utcnow()


class IdentityResolver:
    def __init__(self, users: Iterable[User]) -> None:
        self.by_username = {u.username.casefold(): u.id for u in users}
        names: dict[str, list[int]] = defaultdict(list)
        for user in users:
            names[" ".join(user.full_name.split()).casefold()].append(user.id)
        self.by_name = names

    def resolve(self, raw: str) -> tuple[int | None, str]:
        key = " ".join(str(raw or "").split()).casefold()
        if not key:
            return None, "identity is blank"
        if key in self.by_username:
            return self.by_username[key], ""
        matches = self.by_name.get(key, [])
        if len(matches) == 1:
            return matches[0], ""
        if len(matches) > 1:
            return None, "full name matches multiple users"
        return None, "identity does not match a user"


def _backup(source_dir: Path, target_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = target_root / f"legacy-import-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, str] = {}
    for source in sorted(source_dir.glob("*.csv")):
        shutil.copy2(source, target / source.name)
        manifest[source.name] = _sha(source)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _quarantine(
    repo: LegacyRepository,
    source: str,
    row_number: int,
    reason: str,
    row: dict[str, str],
    dry_run: bool,
) -> None:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
    if not dry_run:
        repo.add_quarantine(
            MigrationQuarantine(
                source_name=source,
                row_number=row_number,
                reason=reason[:240],
                payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                payload_json=payload,
            )
        )


def run_import(source_dir: Path, *, dry_run: bool = True, backup_dir: Path | None = None) -> ImportReport:
    source_dir = source_dir.resolve()
    files = {
        "homework": source_dir / "homework.csv",
        "submissions": source_dir / "homework_submissions.csv",
        "projects": source_dir / "projects.csv",
        "project_files": source_dir / "project_file_meta.csv",
        "notifications": source_dir / "notifications.csv",
    }
    tables = {name: _read(path) for name, path in files.items()}
    hashes = {path.name: _sha(path) for path in files.values() if path.exists()}
    counters = {name: Counter() for name in ("would", "inserted", "skipped", "quarantine", "unresolved")}
    backup = ""
    if not dry_run:
        if backup_dir is None:
            raise ValueError("--apply requires --backup-dir so the original CSV files are preserved")
        backup = str(_backup(source_dir, backup_dir.resolve()))

    with session_scope() as session:
        repo = LegacyRepository(session)
        resolver = IdentityResolver(UserRepository(session).list_by_role())
        valid_source_homework = {
            row.get("Homework ID", "").strip()
            for row in tables["homework"]
            if row.get("Homework ID", "").strip() and row.get("Title", "").strip()
        }
        valid_source_projects = {
            row.get("Project ID", "").strip()
            for row in tables["projects"]
            if row.get("Project ID", "").strip() and row.get("Title", "").strip()
        }

        for number, row in enumerate(tables["homework"], start=2):
            legacy_id = row.get("Homework ID", "").strip()
            if not legacy_id or not row.get("Title", "").strip():
                counters["quarantine"]["homework"] += 1
                _quarantine(repo, files["homework"].name, number, "missing homework id or title", row, dry_run)
                continue
            existing = repo.homework_by_legacy_id(legacy_id)
            if existing:
                counters["skipped"]["homework"] += 1
                continue
            creator_id, reason = resolver.resolve(row.get("Created By", ""))
            if reason:
                counters["unresolved"]["homework_creator"] += 1
            audience = [part.strip() for part in row.get("Assigned To", "").split(",") if part.strip()]
            counters["would"]["homework"] += 1
            if not dry_run:
                repo.add_homework(
                    HomeworkAssignment(
                        legacy_id=legacy_id,
                        title=row.get("Title", "").strip()[:160],
                        topic=row.get("Topic", "").strip()[:120],
                        instructions=row.get("Instructions", ""),
                        due_text=row.get("Due Date", "")[:120],
                        difficulty=row.get("Difficulty", "")[:32],
                        assigned_to_json=json.dumps(audience, ensure_ascii=False),
                        created_by_id=creator_id,
                        attachment_path=row.get("Attachment", "")[:500],
                        is_published=_truthy(row.get("Published", "")),
                        created_at=_date(row.get("Created At", "")),
                    )
                )
                counters["inserted"]["homework"] += 1

        for number, row in enumerate(tables["submissions"], start=2):
            legacy_id = row.get("Submission ID", "").strip()
            homework_legacy_id = row.get("Homework ID", "").strip()
            assignment = repo.homework_by_legacy_id(homework_legacy_id)
            assignment_known = assignment is not None or (dry_run and homework_legacy_id in valid_source_homework)
            student_id, identity_reason = resolver.resolve(row.get("Student", ""))
            if not legacy_id or not assignment_known or student_id is None:
                reason = "missing submission id, homework relationship, or unambiguous student"
                if identity_reason:
                    reason += f" ({identity_reason})"
                counters["quarantine"]["submissions"] += 1
                _quarantine(repo, files["submissions"].name, number, reason, row, dry_run)
                continue
            if repo.submission_by_legacy_id(legacy_id):
                counters["skipped"]["submissions"] += 1
                continue
            counters["would"]["submissions"] += 1
            if not dry_run:
                if assignment is None:
                    raise RuntimeError("Validated homework relationship disappeared during import.")
                repo.add_submission(
                    HomeworkSubmission(
                        legacy_id=legacy_id,
                        assignment_id=assignment.id,
                        student_id=student_id,
                        score=_number(row.get("Score", "")),
                        total=_number(row.get("Total", "")),
                        percentage=_number(row.get("Percentage", "")),
                        attempt=_integer(row.get("Attempt", "")),
                        status=row.get("Status", "submitted")[:24],
                        submitted_at=_date(row.get("Submitted At", "")),
                    )
                )
                counters["inserted"]["submissions"] += 1

        for number, row in enumerate(tables["projects"], start=2):
            legacy_id = row.get("Project ID", "").strip()
            if not legacy_id or not row.get("Title", "").strip():
                counters["quarantine"]["projects"] += 1
                _quarantine(repo, files["projects"].name, number, "missing project id or title", row, dry_run)
                continue
            existing = repo.project_by_legacy_id(legacy_id)
            if existing:
                counters["skipped"]["projects"] += 1
                continue
            creator_id, creator_reason = resolver.resolve(row.get("Created By", ""))
            owner_id, owner_reason = resolver.resolve(row.get("Owner", ""))
            if creator_reason:
                counters["unresolved"]["project_creator"] += 1
            if row.get("Type", "class").casefold() == "personal" and owner_id is None:
                counters["quarantine"]["projects"] += 1
                _quarantine(repo, files["projects"].name, number, owner_reason or "personal project owner missing", row, dry_run)
                continue
            counters["would"]["projects"] += 1
            if not dry_run:
                repo.add_project(
                    LearningProject(
                        legacy_id=legacy_id,
                        title=row.get("Title", "")[:180],
                        description=row.get("Description", ""),
                        due_text=row.get("Due Date", "")[:120],
                        project_type=row.get("Type", "class")[:20],
                        status=row.get("Status", "In Progress")[:24],
                        is_published=_truthy(row.get("Published", "")),
                        created_by_id=creator_id,
                        owner_id=owner_id,
                        created_at=_date(row.get("Created At", "")),
                    )
                )
                counters["inserted"]["projects"] += 1

        for number, row in enumerate(tables["project_files"], start=2):
            legacy_id = row.get("file_id", "").strip()
            project_legacy_id = row.get("project_id", "").strip()
            project = repo.project_by_legacy_id(project_legacy_id)
            project_known = project is not None or (dry_run and project_legacy_id in valid_source_projects)
            uploader_id, identity_reason = resolver.resolve(row.get("uploader", ""))
            if not legacy_id or not project_known or uploader_id is None:
                counters["quarantine"]["project_files"] += 1
                _quarantine(
                    repo,
                    files["project_files"].name,
                    number,
                    f"missing file/project/uploader relationship ({identity_reason})",
                    row,
                    dry_run,
                )
                continue
            if repo.file_by_legacy_id(legacy_id):
                counters["skipped"]["project_files"] += 1
                continue
            object_key = row.get("local_path", "")[:500]
            counters["would"]["project_files"] += 1
            if not dry_run:
                if project is None:
                    raise RuntimeError("Validated project relationship disappeared during import.")
                repo.add_file(
                    ProjectFile(
                        legacy_id=legacy_id,
                        project_id=project.id,
                        uploaded_by_id=uploader_id,
                        filename=Path(row.get("file_name", "upload")).name[:180],
                        object_key=object_key,
                        mime_type=row.get("file_type", "")[:120],
                        notes=row.get("notes", ""),
                        created_at=_date(row.get("created_at", "")),
                    )
                )
                counters["inserted"]["project_files"] += 1

        for number, row in enumerate(tables["notifications"], start=2):
            if row.get("Type", "").casefold() != "announcement":
                continue
            legacy_id = row.get("Notification ID", "").strip()
            audience_id, identity_reason = resolver.resolve(row.get("Student", ""))
            if not legacy_id or audience_id is None:
                counters["quarantine"]["announcements"] += 1
                _quarantine(repo, files["notifications"].name, number, identity_reason or "missing id", row, dry_run)
                continue
            if repo.announcement_by_legacy_id(legacy_id):
                counters["skipped"]["announcements"] += 1
                continue
            counters["would"]["announcements"] += 1
            if not dry_run:
                repo.add_announcement(
                    Announcement(
                        legacy_id=legacy_id,
                        title=row.get("Title", "Announcement")[:180],
                        message=row.get("Message", ""),
                        audience_json=json.dumps([audience_id]),
                        created_at=_date(row.get("Created At", "")),
                    )
                )
                counters["inserted"]["announcements"] += 1

        if dry_run:
            session.rollback()

    return ImportReport(
        dry_run=dry_run,
        source_dir=str(source_dir),
        source_hashes=hashes,
        rows_seen={name: len(rows) for name, rows in tables.items()},
        would_insert=dict(counters["would"]),
        inserted=dict(counters["inserted"]),
        skipped_existing=dict(counters["skipped"]),
        quarantined=dict(counters["quarantine"]),
        unresolved_optional_identities=dict(counters["unresolved"]),
        backup_dir=backup,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Directory containing copied legacy CSV files")
    parser.add_argument("--apply", action="store_true", help="Commit the import; default is dry-run")
    parser.add_argument("--backup-dir", type=Path, help="Required with --apply; receives immutable source copies")
    parser.add_argument("--report", type=Path, help="Optional JSON report output")
    args = parser.parse_args()
    if args.apply and args.backup_dir is None:
        parser.error("--apply requires --backup-dir")
    report = run_import(args.source_dir, dry_run=not args.apply, backup_dir=args.backup_dir)
    payload = json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
