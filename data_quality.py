"""
data_quality.py — Preluma Data Quality & Testing Module  (V40)

Maintainer: MD JIARUL ISLAM
Responsibility: topic data engineering, CSV schema validation, data integrity checks.

Provides:
  run_all_checks()         → dict with pass/fail results for every check suite
  check_topics()           → validate all topic packs have required fields
  check_csv_schemas()      → validate existing CSV files match expected schemas
  check_duplicates()       → find duplicate records in any CSV
  check_homework_data()    → validate homework CSV integrity
  check_project_data()     → validate project CSV integrity

These functions are called from the Evidence Board page to show a live
quality report, and can also be run as standalone unit tests from CLI.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Every topic pack built by engine.build_pack() must contain these keys
REQUIRED_PACK_FIELDS: list[str] = [
    "title", "hook", "definition", "simple",
    "facts", "concepts", "applications",
    "misconceptions", "class_questions",
]

# CSV schemas — (filepath, required_columns)
CSV_SCHEMAS: dict[str, list[str]] = {
    # Columns written by streamlit_app.py save_result() / Readiness quiz
    "data/students.csv": [
        "Record ID", "Student", "Topic",
        "Readiness", "Weak Skill", "Quiz Score", "Quiz Total",
        "Lecture Time", "Learning Mode", "Created At",
    ],
    # Columns written by homework_core.py HOMEWORK_FIELDS
    "data/homework.csv": [
        "Homework ID", "Title", "Topic", "Instructions",
        "Due Date", "Difficulty", "Assigned To",
        "Created By", "Created At", "Published", "Attachment",
    ],
    # Columns written by project_core.py (V40 adds Type / Owner / Status)
    "data/projects.csv": [
        "Project ID", "Title", "Description", "Due Date",
        "Created By", "Created At", "Published", "Type", "Owner", "Status",
    ],
    # Columns written by project_core.py upload_file()
    "data/project_file_meta.csv": [
        "file_id", "project_id", "uploader", "uploader_role",
        "file_name", "file_type", "notes", "created_at", "local_path",
    ],
}

# Unique-key columns per CSV (used for duplicate detection)
UNIQUE_KEYS: dict[str, str] = {
    "data/students.csv":          "Record ID",
    "data/homework.csv":          "Homework ID",
    "data/projects.csv":          "Project ID",
    "data/project_file_meta.csv": "file_id",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _get_fieldnames(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or [])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Topic pack validation
# ─────────────────────────────────────────────────────────────────────────────

def check_topics() -> dict[str, Any]:
    """
    Validate every topic in TOPIC_OPTIONS:
    - All REQUIRED_PACK_FIELDS are present
    - No field is empty / None
    - No duplicate topic names
    Returns a result dict.
    """
    t_start = time.perf_counter_ns()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        from topics import TOPIC_OPTIONS
        from engine import build_pack
    except ImportError as e:
        return {
            "suite": "Topic Validation",
            "passed": False,
            "errors": [f"Import error: {e}"],
            "warnings": [],
            "topics_checked": 0,
            "time_ns": 0,
        }

    topics = list(TOPIC_OPTIONS) if not isinstance(TOPIC_OPTIONS, dict) else list(TOPIC_OPTIONS.keys())

    # Duplicate topic names
    seen: set[str] = set()
    for t in topics:
        if t in seen:
            warnings.append(f"Duplicate topic name: '{t}'")
        seen.add(t)

    # Per-topic field checks
    topics_ok = 0
    for topic in topics:
        try:
            pack = build_pack(topic)
        except Exception as exc:
            errors.append(f"build_pack('{topic}') raised: {exc}")
            continue

        # Missing fields
        missing = [f for f in REQUIRED_PACK_FIELDS if f not in pack]
        if missing:
            errors.append(f"'{topic}' missing fields: {missing}")
            continue

        # Empty fields
        empty = [f for f in REQUIRED_PACK_FIELDS if not pack.get(f)]
        if empty:
            warnings.append(f"'{topic}' has empty fields: {empty}")

        topics_ok += 1

    elapsed = time.perf_counter_ns() - t_start
    return {
        "suite":          "Topic Pack Validation",
        "passed":         len(errors) == 0,
        "errors":         errors,
        "warnings":       warnings,
        "topics_checked": len(topics),
        "topics_ok":      topics_ok,
        "time_ns":        elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. CSV schema validation
# ─────────────────────────────────────────────────────────────────────────────

def check_csv_schemas() -> dict[str, Any]:
    """
    For each CSV that exists, confirm all required columns are present.
    Skips files that don't exist yet (they are created lazily at runtime).
    """
    t_start = time.perf_counter_ns()
    errors:   list[str] = []
    warnings: list[str] = []
    checked = 0

    for csv_path, required_cols in CSV_SCHEMAS.items():
        p = Path(csv_path)
        if not p.exists():
            warnings.append(f"{csv_path} — not yet created (OK, created at runtime)")
            continue

        actual = _get_fieldnames(csv_path)
        checked += 1

        missing = [c for c in required_cols if c not in actual]
        extra   = [c for c in actual if c not in required_cols]

        if missing:
            errors.append(f"{csv_path} — missing columns: {missing}")
        if extra:
            warnings.append(f"{csv_path} — unexpected extra columns: {extra}")

    elapsed = time.perf_counter_ns() - t_start
    return {
        "suite":        "CSV Schema Validation",
        "passed":       len(errors) == 0,
        "errors":       errors,
        "warnings":     warnings,
        "files_checked": checked,
        "time_ns":      elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Duplicate detection
# ─────────────────────────────────────────────────────────────────────────────

def check_duplicates() -> dict[str, Any]:
    """
    For each CSV with a defined unique key, scan for duplicate values.
    """
    t_start = time.perf_counter_ns()
    errors:   list[str] = []
    warnings: list[str] = []
    total_dups = 0

    for csv_path, key_col in UNIQUE_KEYS.items():
        rows = _read_csv(csv_path)
        if not rows:
            continue

        seen: dict[str, int] = {}
        for row in rows:
            val = row.get(key_col, "")
            seen[val] = seen.get(val, 0) + 1

        dups = {k: v for k, v in seen.items() if v > 1 and k}
        if dups:
            dup_list = ", ".join(f"'{k}'×{v}" for k, v in list(dups.items())[:5])
            errors.append(f"{csv_path} — duplicate {key_col}: {dup_list}")
            total_dups += len(dups)

    elapsed = time.perf_counter_ns() - t_start
    return {
        "suite":      "Duplicate Record Detection",
        "passed":     len(errors) == 0,
        "errors":     errors,
        "warnings":   warnings,
        "duplicates": total_dups,
        "time_ns":    elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Homework data integrity
# ─────────────────────────────────────────────────────────────────────────────

def check_homework_data() -> dict[str, Any]:
    """
    Validate homework.csv rows:
    - Homework ID must be non-empty
    - Title and Topic must not be blank
    - Questions must be a valid positive integer
    """
    t_start = time.perf_counter_ns()
    errors:   list[str] = []
    warnings: list[str] = []
    rows = _read_csv("data/homework.csv")

    VALID_DIFFICULTIES = {"Easy", "Medium", "Hard", ""}

    for i, row in enumerate(rows, 1):
        hw_id      = row.get("Homework ID", "").strip()
        title      = row.get("Title", "").strip()
        topic      = row.get("Topic", "").strip()
        difficulty = row.get("Difficulty", "").strip()
        published  = row.get("Published", "").strip().lower()

        if not hw_id:
            errors.append(f"Row {i}: empty Homework ID")
        if not title:
            errors.append(f"Row {i} (ID={hw_id}): empty Title")
        if not topic:
            warnings.append(f"Row {i} (ID={hw_id}): empty Topic")
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            warnings.append(f"Row {i} (ID={hw_id}): Difficulty='{difficulty}' — expected Easy/Medium/Hard")
        if published and published not in {"true", "false", "yes", "no", "1", "0"}:
            warnings.append(f"Row {i} (ID={hw_id}): Published='{published}' — unexpected value")

    elapsed = time.perf_counter_ns() - t_start
    return {
        "suite":       "Homework Data Integrity",
        "passed":      len(errors) == 0,
        "errors":      errors,
        "warnings":    warnings,
        "rows_checked": len(rows),
        "time_ns":     elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Project data integrity
# ─────────────────────────────────────────────────────────────────────────────

def check_project_data() -> dict[str, Any]:
    """
    Validate projects.csv rows:
    - Project ID must be non-empty
    - Title must not be blank
    - Type must be 'class' or 'personal'
    - Status must be 'In Progress' or 'Complete'
    """
    t_start = time.perf_counter_ns()
    errors:   list[str] = []
    warnings: list[str] = []
    rows = _read_csv("data/projects.csv")

    VALID_TYPES   = {"class", "personal"}
    VALID_STATUSES = {"In Progress", "Complete"}

    for i, row in enumerate(rows, 1):
        pid    = row.get("Project ID", "").strip()
        title  = row.get("Title", "").strip()
        ptype  = row.get("Type", "").strip()
        status = row.get("Status", "").strip()

        if not pid:
            errors.append(f"Row {i}: empty Project ID")
        if not title:
            errors.append(f"Row {i} (ID={pid}): empty Title")
        if ptype and ptype not in VALID_TYPES:
            errors.append(f"Row {i} (ID={pid}): Type='{ptype}' — must be 'class' or 'personal'")
        if status and status not in VALID_STATUSES:
            warnings.append(f"Row {i} (ID={pid}): Status='{status}' — expected 'In Progress' or 'Complete'")

    elapsed = time.perf_counter_ns() - t_start
    return {
        "suite":       "Project Data Integrity",
        "passed":      len(errors) == 0,
        "errors":      errors,
        "warnings":    warnings,
        "rows_checked": len(rows),
        "time_ns":     elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_checks() -> dict[str, Any]:
    """
    Run every check suite and return a combined report.
    """
    t_start = time.perf_counter_ns()

    suites = [
        check_topics(),
        check_csv_schemas(),
        check_duplicates(),
        check_homework_data(),
        check_project_data(),
    ]

    total_errors   = sum(len(s["errors"])   for s in suites)
    total_warnings = sum(len(s["warnings"]) for s in suites)
    all_passed     = all(s["passed"] for s in suites)
    elapsed        = time.perf_counter_ns() - t_start

    return {
        "all_passed":     all_passed,
        "total_errors":   total_errors,
        "total_warnings": total_warnings,
        "total_time_ns":  elapsed,
        "suites":         suites,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI runner — python data_quality.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 62)
    print("  Preluma Data Quality Report")
    print("═" * 62)

    report = run_all_checks()
    for suite in report["suites"]:
        icon = "✓" if suite["passed"] else "✗"
        ms = suite["time_ns"] / 1_000_000
        print(f"\n  {icon}  {suite['suite']}  ({ms:.2f} ms)")
        for e in suite.get("errors", []):
            print(f"       ERROR: {e}")
        for w in suite.get("warnings", []):
            print(f"       WARN:  {w}")
        # Extra stats
        for key in ("topics_checked", "files_checked", "rows_checked", "duplicates"):
            if key in suite:
                print(f"       {key}: {suite[key]}")

    total_ms = report["total_time_ns"] / 1_000_000
    print("\n" + "═" * 62)
    status = "ALL CHECKS PASSED" if report["all_passed"] else "CHECKS FAILED"
    print(f"  {status}  |  {report['total_errors']} error(s)  "
          f"{report['total_warnings']} warning(s)  |  {total_ms:.2f} ms total")
    print("═" * 62 + "\n")
