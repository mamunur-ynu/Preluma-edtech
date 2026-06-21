"""
project_core.py — Preluma Project Management Module  (V39.1)

Two project types:
  "class"    — created by teacher, students submit files against it
  "personal" — created by a student; status "In Progress" = private (teacher cannot see),
               status "Complete" = teacher can view and download

Storage:
  • Project metadata  → data/projects.csv  (local, re-creatable)
  • Project files     → Supabase preluma_project_files table (permanent base64 blobs)
                        Falls back to data/project_files/ directory when Supabase unavailable

Supabase table required (run ONCE in Supabase SQL editor):
    create table if not exists preluma_project_files (
      file_id       text primary key,
      project_id    text not null,
      uploader      text not null,
      uploader_role text not null,
      file_name     text not null,
      file_type     text,
      file_data     text not null,
      notes         text,
      created_at    text not null
    );
    alter table preluma_project_files enable row level security;
    create policy "anon full access" on preluma_project_files
      for all using (true) with check (true);
"""
from __future__ import annotations

import base64
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import requests as _requests
from storage_core import backup_csv, restore_csv

DATA_DIR        = Path("data")
PROJECTS_CSV    = DATA_DIR / "projects.csv"
LOCAL_FILES_DIR = DATA_DIR / "project_files"

# Type   : "class" | "personal"
# Status : "In Progress" | "Complete"   (personal projects only)
PROJECT_FIELDS = [
    "Project ID", "Title", "Description", "Due Date",
    "Created By", "Created At", "Published", "Type", "Owner", "Status",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return str(uuid.uuid4())[:10]


def _get_secret(name: str) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        return str(val).strip() if val else ""
    except Exception:
        return ""


def _supabase_available() -> bool:
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))


def _sb_headers() -> dict:
    key = _get_secret("SUPABASE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _sb_files_url() -> str:
    base = _get_secret("SUPABASE_URL").rstrip("/")
    return f"{base}/rest/v1/preluma_project_files"


# ─────────────────────────────────────────────────────────────────────────────
# CSV helpers — project metadata
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_projects_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_CSV.exists():
        if not restore_csv(PROJECTS_CSV, PROJECT_FIELDS):
            with PROJECTS_CSV.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=PROJECT_FIELDS).writeheader()


def _read_projects() -> list[dict]:
    _ensure_projects_csv()
    if not PROJECTS_CSV.exists():
        return []
    rows = []
    with PROJECTS_CSV.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Backward-compat: old rows without Type/Owner/Status
            row.setdefault("Type", "class")
            row.setdefault("Owner", "")
            row.setdefault("Status", "Complete")
            rows.append(row)
    return rows


def _append_project(row: dict) -> None:
    _ensure_projects_csv()
    clean = {field: row.get(field, "") for field in PROJECT_FIELDS}
    with PROJECTS_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=PROJECT_FIELDS).writerow(clean)
    backup_csv(PROJECTS_CSV)


def _rewrite_projects(rows: list[dict]) -> None:
    """Overwrite entire CSV with updated rows."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with PROJECTS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PROJECT_FIELDS)
        w.writeheader()
        for row in rows:
            clean = {field: row.get(field, "") for field in PROJECT_FIELDS}
            w.writerow(clean)
    backup_csv(PROJECTS_CSV)


# ─────────────────────────────────────────────────────────────────────────────
# Supabase file helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sb_upload_file(row: dict) -> bool:
    try:
        resp = _requests.post(
            _sb_files_url(),
            headers={**_sb_headers(), "Prefer": "return=minimal"},
            json=row,
            timeout=30,
        )
        return resp.status_code in (200, 201, 204)
    except Exception:
        return False


def _sb_get_files(project_id: str | None = None,
                  uploader: str | None = None,
                  uploader_role: str | None = None) -> list[dict]:
    params: dict[str, str] = {
        "select": "file_id,project_id,uploader,uploader_role,file_name,file_type,notes,created_at"
    }
    filters = []
    if project_id:
        filters.append(f"project_id=eq.{project_id}")
    if uploader:
        filters.append(f"uploader=eq.{uploader}")
    if uploader_role:
        filters.append(f"uploader_role=eq.{uploader_role}")
    if filters:
        params["and"] = "(" + ",".join(filters) + ")"
    try:
        resp = _requests.get(_sb_files_url(), headers=_sb_headers(), params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def _sb_get_file_data(file_id: str) -> dict | None:
    try:
        resp = _requests.get(
            _sb_files_url(),
            headers=_sb_headers(),
            params={"file_id": f"eq.{file_id}", "select": "*", "limit": "1"},
            timeout=20,
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    except Exception:
        pass
    return None


def _sb_delete_file(file_id: str) -> bool:
    try:
        resp = _requests.delete(
            _sb_files_url(),
            headers=_sb_headers(),
            params={"file_id": f"eq.{file_id}"},
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Local file fallback
# ─────────────────────────────────────────────────────────────────────────────

_LOCAL_META_CSV = DATA_DIR / "project_file_meta.csv"
_LOCAL_META_FIELDS = [
    "file_id", "project_id", "uploader", "uploader_role",
    "file_name", "file_type", "notes", "created_at", "local_path",
]


def _ensure_local_meta() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_FILES_DIR.mkdir(parents=True, exist_ok=True)
    if not _LOCAL_META_CSV.exists():
        with _LOCAL_META_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_LOCAL_META_FIELDS).writeheader()


def _local_save_file(row: dict, file_bytes: bytes) -> bool:
    _ensure_local_meta()
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in row["file_name"])
    local_path = LOCAL_FILES_DIR / f"{row['file_id']}_{safe}"
    try:
        local_path.write_bytes(file_bytes)
        row["local_path"] = str(local_path)
        clean = {f: row.get(f, "") for f in _LOCAL_META_FIELDS}
        with _LOCAL_META_CSV.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_LOCAL_META_FIELDS).writerow(clean)
        return True
    except Exception:
        return False


def _local_get_files(project_id: str | None = None,
                     uploader: str | None = None,
                     uploader_role: str | None = None) -> list[dict]:
    _ensure_local_meta()
    rows = []
    if not _LOCAL_META_CSV.exists():
        return rows
    with _LOCAL_META_CSV.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if project_id and row.get("project_id") != project_id:
                continue
            if uploader and row.get("uploader") != uploader:
                continue
            if uploader_role and row.get("uploader_role") != uploader_role:
                continue
            rows.append(row)
    return rows


def _local_get_file_bytes(file_id: str) -> tuple[bytes | None, str]:
    _ensure_local_meta()
    if not _LOCAL_META_CSV.exists():
        return None, ""
    with _LOCAL_META_CSV.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("file_id") == file_id:
                path = Path(row.get("local_path", ""))
                if path.exists():
                    return path.read_bytes(), row.get("file_name", "file")
    return None, ""


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Projects
# ─────────────────────────────────────────────────────────────────────────────

def create_class_project(title: str, description: str, due_date: str, created_by: str) -> str:
    """Create a teacher-assigned class project. Returns project_id."""
    pid = _new_id()
    _append_project({
        "Project ID": pid,
        "Title":      title.strip(),
        "Description": description.strip(),
        "Due Date":   due_date.strip(),
        "Created By": created_by.strip(),
        "Created At": _now(),
        "Published":  "Yes",
        "Type":       "class",
        "Owner":      "",
        "Status":     "Complete",
    })
    return pid


def create_personal_project(title: str, description: str, owner: str,
                             status: str = "In Progress") -> str:
    """
    Create a student's personal project.
    status = 'In Progress'  →  visible only to the student
    status = 'Complete'     →  visible to teachers as well
    Returns project_id.
    """
    pid = _new_id()
    _append_project({
        "Project ID": pid,
        "Title":      title.strip(),
        "Description": description.strip(),
        "Due Date":   "",
        "Created By": owner.strip(),
        "Created At": _now(),
        "Published":  "Yes",
        "Type":       "personal",
        "Owner":      owner.strip(),
        "Status":     status,
    })
    return pid


def update_project_status(project_id: str, new_status: str) -> bool:
    """Update Status of a personal project ('In Progress' ↔ 'Complete')."""
    rows = _read_projects()
    changed = False
    for row in rows:
        if row.get("Project ID") == project_id:
            row["Status"] = new_status
            changed = True
    if changed:
        _rewrite_projects(rows)
    return changed


def load_class_projects() -> list[dict]:
    """All teacher-created class projects."""
    return [r for r in _read_projects() if r.get("Type", "class") == "class" and r.get("Published") == "Yes"]


def load_personal_projects(owner: str, include_in_progress: bool = True) -> list[dict]:
    """Personal projects owned by a specific student."""
    owner_key = owner.strip().casefold()
    rows = [r for r in _read_projects()
            if r.get("Type") == "personal"
            and r.get("Owner", "").strip().casefold() == owner_key]
    if not include_in_progress:
        rows = [r for r in rows if r.get("Status") == "Complete"]
    return rows


def load_all_complete_personal_projects() -> list[dict]:
    """All students' completed personal projects — for teacher view."""
    return [r for r in _read_projects()
            if r.get("Type") == "personal" and r.get("Status") == "Complete"]


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Files
# ─────────────────────────────────────────────────────────────────────────────

def upload_file(
    project_id: str,
    uploader: str,
    uploader_role: str,
    file_name: str,
    file_bytes: bytes,
    file_type: str = "",
    notes: str = "",
) -> tuple[bool, str]:
    """Upload a file. Returns (success, file_id_or_error)."""
    file_id  = _new_id()
    b64_data = base64.b64encode(file_bytes).decode()
    row = {
        "file_id":       file_id,
        "project_id":    project_id,
        "uploader":      uploader,
        "uploader_role": uploader_role,
        "file_name":     file_name,
        "file_type":     file_type,
        "file_data":     b64_data,
        "notes":         notes,
        "created_at":    _now(),
    }
    if _supabase_available():
        ok = _sb_upload_file(row)
        if ok:
            return True, file_id
    ok = _local_save_file(dict(row), file_bytes)
    return ok, file_id if ok else "Upload failed"


def get_project_files(
    project_id: str | None = None,
    uploader: str | None = None,
    uploader_role: str | None = None,
) -> list[dict]:
    """Metadata only — no binary data. Fast for listing."""
    if _supabase_available():
        rows = _sb_get_files(project_id, uploader, uploader_role)
        if rows is not None:
            return rows
    return _local_get_files(project_id, uploader, uploader_role)


def download_file(file_id: str) -> tuple[bytes | None, str, str]:
    """Returns (bytes, file_name, mime_type)."""
    if _supabase_available():
        rec = _sb_get_file_data(file_id)
        if rec:
            try:
                raw = base64.b64decode(rec["file_data"])
                return raw, rec.get("file_name", "file"), rec.get("file_type", "")
            except Exception:
                pass
    raw, fname = _local_get_file_bytes(file_id)
    return raw, fname, ""


def delete_file(file_id: str) -> bool:
    if _supabase_available():
        return _sb_delete_file(file_id)
    return False


def student_has_uploaded(project_id: str, student: str) -> bool:
    files = get_project_files(project_id=project_id, uploader=student, uploader_role="student")
    return len(files) > 0
