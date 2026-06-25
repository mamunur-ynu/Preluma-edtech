"""
storage_core.py
---------------
Data persistence layer for the Preluma pre-class preparation system.

This module manages two storage backends:

  Local CSV files
    Fast and reliable for development. Stored in the /data directory relative
    to the working directory. On Streamlit Cloud these files are ephemeral —
    they are cleared on every new deploy — so CSV is used as a write-through
    cache, not as the primary store.

  Supabase (remote database)
    Active when SUPABASE_URL and SUPABASE_KEY are present in Streamlit secrets.
    All CSV rows are serialised to JSON and pushed to a single generic key-value
    table called 'preluma_data_store'. This design keeps the Supabase schema
    minimal (one table, two columns: key and value) while still supporting any
    number of CSV files.

The key public functions are:
  backup_csv()  — push a local CSV to Supabase as a JSON blob.
  restore_csv() — pull from Supabase and write into a local CSV file.

All other functions in this file support the student result log and are used
by streamlit_app.py to record and display learning history.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


DATA_DIR     = Path("data")
STUDENTS_CSV = DATA_DIR / "students.csv"
RESULT_LOG   = Path("result.txt")

# Column names for the student result records written after each mission.
FIELDNAMES = [
    "Record ID", "Student", "Topic", "Readiness", "Weak Skill",
    "Quiz Score", "Quiz Total", "Lecture Time", "Learning Mode", "Created At",
]

# Supabase table used for all CSV backups (key-value design).
_SB_DATA_TABLE = "preluma_data_store"


# ---------------------------------------------------------------------------
# Secret / configuration helpers
# ---------------------------------------------------------------------------

def _get_secret(name: str) -> str:
    """
    Read a value from Streamlit secrets, falling back to an environment
    variable if Streamlit is not running (e.g. during tests or local scripts).
    Returns an empty string when neither source has the value.
    """
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        return str(val).strip() if val else ""
    except Exception:
        return str(os.environ.get(name, "")).strip()


def _sb_available() -> bool:
    """Return True when both Supabase credentials are present."""
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))


def _sb_data_url() -> str:
    """Build the full REST endpoint URL for the Supabase data store table."""
    return _get_secret("SUPABASE_URL").rstrip("/") + f"/rest/v1/{_SB_DATA_TABLE}"


def _sb_hdrs() -> dict:
    """Return the HTTP headers required for all Supabase REST requests."""
    k = _get_secret("SUPABASE_KEY")
    return {
        "apikey":        k,
        "Authorization": f"Bearer {k}",
        "Content-Type":  "application/json",
    }


# ---------------------------------------------------------------------------
# Supabase backup and restore
# ---------------------------------------------------------------------------

def backup_csv(csv_path: Path) -> bool:
    """
    Serialise a local CSV file to JSON and push it to Supabase.

    The row data is stored under a key equal to the CSV filename (e.g.
    'students.csv'). An upsert is used so repeated calls update the existing
    record rather than creating duplicate rows.

    Returns True on success. Any network or serialisation error is caught,
    logged to stdout for visibility in Streamlit Cloud logs, and returns False
    rather than crashing the app.
    """
    if not _sb_available():
        return False
    try:
        import requests
        rows: list[dict] = []
        if csv_path.exists():
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                rows = [dict(r) for r in csv.DictReader(f)]

        resp = requests.post(
            _sb_data_url(),
            headers={**_sb_hdrs(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json={"key": csv_path.name, "value": json.dumps(rows)},
            timeout=15,
        )
        success = resp.status_code in (200, 201, 204)
        if not success:
            print(f"[storage] backup failed for {csv_path.name}: "
                  f"HTTP {resp.status_code} — {resp.text[:200]}")
        return success
    except Exception as exc:
        print(f"[storage] backup exception for {csv_path.name}: {exc}")
        return False


def restore_csv(csv_path: Path, fields: list[str]) -> bool:
    """
    Pull a previously backed-up CSV from Supabase and write it to disk.

    The stored JSON blob is deserialised back into rows and written with the
    correct header. Returns True if at least one row was restored. Returns
    False if Supabase is unavailable, the key was not found, or an error occurs.

    This function is called at app startup so that data written during a
    previous deploy is available again after the local filesystem was cleared.
    """
    if not _sb_available():
        return False
    try:
        import requests
        resp = requests.get(
            _sb_data_url(),
            headers=_sb_hdrs(),
            params={"key": f"eq.{csv_path.name}", "select": "value"},
            timeout=10,
        )
        rows_raw = resp.json()
        if rows_raw and isinstance(rows_raw, list) and rows_raw[0].get("value"):
            data = json.loads(rows_raw[0]["value"])
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(data)
            print(f"[storage] restored {csv_path.name} — {len(data)} rows")
            return True
    except Exception as exc:
        print(f"[storage] restore exception for {csv_path.name}: {exc}")
    return False


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def timestamp() -> str:
    """Return the current local time as a compact ISO 8601 string."""
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Student result storage
# ---------------------------------------------------------------------------

def ensure_data_files() -> None:
    """
    Guarantee that the students CSV and result log exist before any read or write.

    For the students CSV, Supabase is checked first so that historical records
    reappear automatically after a deploy. If Supabase has no data, a blank
    file with the correct header is created locally.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not STUDENTS_CSV.exists():
        if not restore_csv(STUDENTS_CSV, FIELDNAMES):
            with STUDENTS_CSV.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

    if not RESULT_LOG.exists():
        RESULT_LOG.write_text("Preluma Audit Log\n", encoding="utf-8")


def load_student_rows() -> list[dict[str, Any]]:
    """
    Read all student result records and normalise numeric columns.

    Record ID, Quiz Score, and Quiz Total are cast to int; Readiness is cast
    to float. Invalid values silently become zero rather than raising exceptions,
    which keeps the analytics charts stable even if a row is partially corrupted.
    """
    ensure_data_files()
    rows: list[dict[str, Any]] = []
    with STUDENTS_CSV.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for field in ["Record ID", "Quiz Score", "Quiz Total"]:
                try:
                    row[field] = int(row.get(field, 0))
                except (TypeError, ValueError):
                    row[field] = 0
            try:
                row["Readiness"] = float(row.get("Readiness", 0.0))
            except (TypeError, ValueError):
                row["Readiness"] = 0.0
            rows.append(row)
    return rows


def next_record_id() -> int:
    """
    Return the next available integer Record ID.

    Scans all existing rows and returns max(existing_id) + 1. An empty file
    returns 1, which is correct for the first record.
    """
    max_id = 0
    for row in load_student_rows():
        try:
            max_id = max(max_id, int(row.get("Record ID", 0)))
        except (TypeError, ValueError):
            pass
    return max_id + 1


def append_student_row(row: dict[str, Any]) -> None:
    """
    Append one student result row to the CSV and immediately back it up.

    Only the fields listed in FIELDNAMES are written, so extra keys in the
    dict are safely ignored. The Supabase backup happens synchronously so
    the data is safe before the function returns.
    """
    ensure_data_files()
    clean = {field: row.get(field, "") for field in FIELDNAMES}
    with STUDENTS_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(clean)
    backup_csv(STUDENTS_CSV)


def append_result_log(operation: str, details: dict[str, Any]) -> None:
    """
    Write a structured audit entry to the plain-text result log.

    Each line records the timestamp, operation name, and all detail key-value
    pairs separated by ' | '. This log is visible in the teacher's admin panel
    for basic activity monitoring.
    """
    ensure_data_files()
    parts = [f"{timestamp()} | op={operation}"]
    for key, value in details.items():
        parts.append(f"{key}={value}")
    with RESULT_LOG.open("a", encoding="utf-8") as f:
        f.write(" | ".join(parts) + "\n")


def read_recent_logs(limit: int = 10) -> list[str]:
    """
    Return the most recent lines from the result log.

    Empty lines are filtered out before counting so that blank formatting
    lines do not consume slots in the returned list.
    """
    ensure_data_files()
    lines = [
        line for line in RESULT_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return lines[-limit:]


# ---------------------------------------------------------------------------
# Demo data seeder
# ---------------------------------------------------------------------------

def seed_demo_rows() -> None:
    """
    Insert a representative set of sample results if the system has no data.

    This runs on first launch so the teacher dashboard charts and tables
    are immediately populated with realistic-looking entries. The function
    does nothing if any student record already exists.
    """
    ensure_data_files()
    if load_student_rows():
        return

    demo = [
        ("Amir",   "Quantum Mechanics",      85.0, "Core Concept",  3, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Jia",    "Neural Network",          92.0, "None",          4, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Fahim",  "Python Programming",      76.0, "Application",   3, 4, "Tomorrow 9 AM", "Exam/Viva Mode"),
        ("Nadia",  "Statistics",              68.0, "Definition",    2, 4, "Tomorrow 9 AM", "Fast Review"),
        ("Omar",   "Machine Learning",        88.0, "None",          4, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Sara",   "Artificial Intelligence", 72.0, "Misconception", 3, 4, "Tomorrow 9 AM", "Normal Mode"),
    ]

    for rid, (student, topic, readiness, weak, score, total, lecture, mode) in enumerate(demo, start=1):
        append_student_row({
            "Record ID":    rid,
            "Student":      student,
            "Topic":        topic,
            "Readiness":    readiness,
            "Weak Skill":   weak,
            "Quiz Score":   score,
            "Quiz Total":   total,
            "Lecture Time": lecture,
            "Learning Mode":mode,
            "Created At":   timestamp(),
        })

    append_result_log("seed_demo_rows", {"n": len(demo)})
