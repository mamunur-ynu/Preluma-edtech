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
FIELDNAMES   = ["Record ID","Student","Topic","Readiness","Weak Skill",
                "Quiz Score","Quiz Total","Lecture Time","Learning Mode","Created At"]

# ─── Supabase generic data store ─────────────────────────────────────────────
_SB_DATA_TABLE = "preluma_data_store"

def _get_secret(name: str) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        return str(val).strip() if val else ""
    except Exception:
        return str(os.environ.get(name, "")).strip()

def _sb_available() -> bool:
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))

def _sb_data_url() -> str:
    return _get_secret("SUPABASE_URL").rstrip("/") + f"/rest/v1/{_SB_DATA_TABLE}"

def _sb_hdrs() -> dict:
    k = _get_secret("SUPABASE_KEY")
    return {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}

def backup_csv(csv_path: Path) -> bool:
    """Push entire CSV to Supabase as a JSON blob (upsert by filename key)."""
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
        ok = resp.status_code in (200, 201, 204)
        if not ok:
            print(f"[sb_backup] {csv_path.name} → {resp.status_code}: {resp.text[:200]}")
        return ok
    except Exception as e:
        print(f"[sb_backup] {csv_path.name} exception: {e}")
        return False

def restore_csv(csv_path: Path, fields: list[str]) -> bool:
    """Pull CSV from Supabase into local file. Returns True if data was found."""
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
            print(f"[sb_restore] {csv_path.name} ← {len(data)} rows")
            return True
    except Exception as e:
        print(f"[sb_restore] {csv_path.name} exception: {e}")
    return False

# ─── Core data functions ──────────────────────────────────────────────────────

def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")

def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STUDENTS_CSV.exists():
        # Try Supabase first
        if not restore_csv(STUDENTS_CSV, FIELDNAMES):
            with STUDENTS_CSV.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()
    if not RESULT_LOG.exists():
        RESULT_LOG.write_text("Preluma Audit Log\n", encoding="utf-8")

def load_student_rows() -> list[dict[str, Any]]:
    ensure_data_files()
    rows = []
    with STUDENTS_CSV.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for field in ["Record ID","Quiz Score","Quiz Total"]:
                try: row[field] = int(row.get(field, 0))
                except (TypeError, ValueError): row[field] = 0
            try: row["Readiness"] = float(row.get("Readiness", 0.0))
            except (TypeError, ValueError): row["Readiness"] = 0.0
            rows.append(row)
    return rows

def next_record_id() -> int:
    max_id = 0
    for row in load_student_rows():
        try: max_id = max(max_id, int(row.get("Record ID", 0)))
        except (TypeError, ValueError): pass
    return max_id + 1

def append_student_row(row: dict[str, Any]) -> None:
    ensure_data_files()
    clean = {field: row.get(field, "") for field in FIELDNAMES}
    with STUDENTS_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(clean)
    backup_csv(STUDENTS_CSV)  # persist to Supabase immediately

def append_result_log(operation: str, details: dict[str, Any]) -> None:
    ensure_data_files()
    parts = [f"{timestamp()} | op={operation}"]
    for key, value in details.items():
        parts.append(f"{key}={value}")
    with RESULT_LOG.open("a", encoding="utf-8") as f:
        f.write(" | ".join(parts) + "\n")

def read_recent_logs(limit: int = 10) -> list[str]:
    ensure_data_files()
    lines = [l for l in RESULT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lines[-limit:]

def seed_demo_rows() -> None:
    ensure_data_files()
    if load_student_rows():
        return
    demo = [
        ("Amir",   "Quantum Mechanics",       85.0, "Core Concept", 3, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Jia",    "Neural Network",           92.0, "None",         4, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Fahim",  "Python Programming",       76.0, "Application",  3, 4, "Tomorrow 9 AM", "Exam/Viva Mode"),
        ("Nadia",  "Statistics",               68.0, "Definition",   2, 4, "Tomorrow 9 AM", "Fast Review"),
        ("Omar",   "Machine Learning",         88.0, "None",         4, 4, "Tomorrow 9 AM", "Deep Understanding"),
        ("Sara",   "Artificial Intelligence",  72.0, "Misconception",3, 4, "Tomorrow 9 AM", "Normal Mode"),
    ]
    rid = 1
    for student, topic, readiness, weak, score, total, lecture, mode in demo:
        append_student_row({
            "Record ID": rid, "Student": student, "Topic": topic,
            "Readiness": readiness, "Weak Skill": weak,
            "Quiz Score": score, "Quiz Total": total,
            "Lecture Time": lecture, "Learning Mode": mode,
            "Created At": timestamp()
        })
        rid += 1
    append_result_log("seed_demo_rows", {"n": len(demo)})
