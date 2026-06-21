"""
auth.py — Preluma Authentication Module

Storage strategy (in priority order):
  1. Supabase  — if SUPABASE_URL + SUPABASE_KEY are in Streamlit secrets.
                 Data survives every deploy forever.
  2. CSV file  — fallback when Supabase is not configured.
                 Ephemeral on Streamlit Cloud (resets on each deploy).
                 Reliable for local dev.

Permanent accounts live in DEMO_USERS below and are re-seeded on every
startup so they ALWAYS exist regardless of which backend is in use.

Passwords stored as SHA-256 hashes — no external libraries needed.
"""
from __future__ import annotations

import csv
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests as _requests

DATA_DIR  = Path("data")
USERS_CSV = DATA_DIR / "users.csv"
USER_FIELDS = ["User ID", "Username", "Password Hash", "Role", "Full Name", "Created At"]

# ─────────────────────────────────────────────────────────────────────────────
# PERMANENT ACCOUNTS — add anyone here who must always exist after a deploy.
# Format: (username, password, role, full_name)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_USERS = [
    # ── Admin / Team ──────────────────────────────────────────────────────
    ("teacher",     "teach123",    "teacher", "Prof. Amir Hossain"),
    ("mim.ynu",     "MimYnu24",    "teacher", "Mamunur Rashid (Admin)"),
    # ── Course Teachers ───────────────────────────────────────────────────
    ("zhouyujue",   "Zhou2024",    "teacher", "Zhou Yujue"),
    ("gaosong",     "Gao2024",     "teacher", "Gao Song"),
    ("tangli",      "Tang2024",    "teacher", "Tang Li"),
    ("weiping",     "Wei2024",     "teacher", "Wei Ping"),
    # ── Dev Team / Inventors (hidden admin access) ───────────────────────
    ("mamun",       "preluma1",    "teacher", "Mamunur Rashid"),
    ("fahim",       "preluma1",    "teacher", "Md Fahim"),
    ("jiarul",      "preluma1",    "teacher", "Jiarul Islam"),
    # ── Demo Students ─────────────────────────────────────────────────────
    ("student1",    "pass123",     "student", "Alice Wang"),
    ("student2",    "pass123",     "student", "Bob Chen"),
    # ── Class Demo ────────────────────────────────────────────────────────
    ("class_demo",  "preluma123",  "student", "Class Demo"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _get_secret(name: str) -> str:
    """Read from Streamlit secrets, fall back to empty string."""
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        return str(val).strip() if val else ""
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Supabase backend
# ─────────────────────────────────────────────────────────────────────────────

def _sb_headers() -> dict:
    key = _get_secret("SUPABASE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _sb_url() -> str:
    base = _get_secret("SUPABASE_URL").rstrip("/")
    return f"{base}/rest/v1/preluma_users"


def _supabase_available() -> bool:
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))


def _sb_read_all() -> list[dict]:
    try:
        resp = _requests.get(
            _sb_url(),
            headers={**_sb_headers(), "Prefer": "return=representation"},
            params={"select": "user_id,username,password_hash,role,full_name,created_at"},
            timeout=8,
        )
        resp.raise_for_status()
        rows = resp.json()
        return [{
            "User ID":       r.get("user_id", ""),
            "Username":      r.get("username", ""),
            "Password Hash": r.get("password_hash", ""),
            "Role":          r.get("role", "student"),
            "Full Name":     r.get("full_name", ""),
            "Created At":    r.get("created_at", ""),
        } for r in rows]
    except Exception:
        return []


def _sb_upsert(row: dict) -> bool:
    payload = {
        "user_id":       row["User ID"],
        "username":      row["Username"],
        "password_hash": row["Password Hash"],
        "role":          row["Role"],
        "full_name":     row["Full Name"],
        "created_at":    row["Created At"],
    }
    try:
        resp = _requests.post(
            _sb_url(),
            headers={**_sb_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=payload,
            timeout=8,
        )
        return resp.status_code in (200, 201, 204)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CSV backend  (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _csv_read_all() -> list[dict]:
    if not USERS_CSV.exists():
        return []
    with USERS_CSV.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _csv_append(row: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    needs_header = not USERS_CSV.exists()
    with USERS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=USER_FIELDS)
        if needs_header:
            w.writeheader()
        w.writerow(row)


# ─────────────────────────────────────────────────────────────────────────────
# Unified read / write
# ─────────────────────────────────────────────────────────────────────────────

def _read_all() -> list[dict]:
    if _supabase_available():
        rows = _sb_read_all()
        if rows:
            return rows
        return rows
    return _csv_read_all()


def _write_row(row: dict) -> None:
    if _supabase_available():
        _sb_upsert(row)
    else:
        _csv_append(row)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

_SETUP_DONE: bool = False

def ensure_setup() -> None:
    global _SETUP_DONE
    if _SETUP_DONE:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _supabase_available():
        # Always upsert DEMO_USERS so roles/names stay in sync with code
        for username, password, role, full_name in DEMO_USERS:
            uname = username.strip().lower()
            _sb_upsert({
                "User ID":       _new_id(),
                "Username":      uname,
                "Password Hash": _hash(password),
                "Role":          role,
                "Full Name":     full_name.strip(),
                "Created At":    _now(),
            })
    else:
        existing = {u["Username"] for u in _csv_read_all()}
        for username, password, role, full_name in DEMO_USERS:
            uname = username.strip().lower()
            if uname not in existing:
                _csv_append({
                    "User ID":       _new_id(),
                    "Username":      uname,
                    "Password Hash": _hash(password),
                    "Role":          role,
                    "Full Name":     full_name.strip(),
                    "Created At":    _now(),
                })
                existing.add(uname)
    _SETUP_DONE = True


def authenticate(username: str, password: str) -> Optional[dict]:
    uname, pw_hash = username.strip().lower(), _hash(password)

    for demo_uname, demo_pw, demo_role, demo_name in DEMO_USERS:
        if demo_uname.strip().lower() == uname and _hash(demo_pw) == pw_hash:
            return {
                "User ID":       "demo",
                "Username":      uname,
                "Password Hash": pw_hash,
                "Role":          demo_role,
                "Full Name":     demo_name,
                "Created At":    "",
            }

    ensure_setup()
    for u in _read_all():
        if u["Username"] == uname and u["Password Hash"] == pw_hash:
            return u
    return None


def username_exists(username: str) -> bool:
    uname = username.strip().lower()
    # Check DEMO_USERS first
    for demo_uname, _, _, _ in DEMO_USERS:
        if demo_uname.strip().lower() == uname:
            return True
    return uname in {u["Username"] for u in _read_all()}


def register(username: str, password: str, full_name: str,
             role: str = "student") -> tuple[bool, str]:
    uname = username.strip().lower()
    if not uname or not password or not full_name.strip():
        return False, "All fields are required."
    if len(uname) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    ensure_setup()
    if username_exists(uname):
        return False, "Username already taken. Please choose another."
    _write_row({
        "User ID":       _new_id(),
        "Username":      uname,
        "Password Hash": _hash(password),
        "Role":          role,
        "Full Name":     full_name.strip(),
        "Created At":    _now(),
    })
    return True, "Account created successfully!"


def reset_password(username: str, new_password: str) -> tuple[bool, str]:
    """Reset password for an existing user (by username)."""
    uname = username.strip().lower()
    if not uname:
        return False, "Please enter your username."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."
    ensure_setup()
    if not username_exists(uname):
        return False, "Account not found. Please check your username."
    new_hash = _hash(new_password)
    if _supabase_available():
        try:
            base = _get_secret("SUPABASE_URL").rstrip("/")
            _requests.patch(
                f"{base}/rest/v1/preluma_users?username=eq.{uname}",
                headers={**_sb_headers(), "Prefer": "return=minimal"},
                json={"password_hash": new_hash},
                timeout=8,
            )
        except Exception:
            pass
    users = _csv_read_all()
    updated = False
    for u in users:
        if u.get("Username") == uname:
            u["Password Hash"] = new_hash
            updated = True
    if updated:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with USERS_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=USER_FIELDS)
            w.writeheader()
            w.writerows(users)
    return True, "Password reset successfully! You can now log in."


def get_all_students() -> list[dict]:
    ensure_setup()
    return [u for u in _read_all() if u["Role"] == "student"]


def get_all_users() -> list[dict]:
    ensure_setup()
    return _read_all()


def storage_backend() -> str:
    return "supabase" if _supabase_available() else "csv"


# ─────────────────────────────────────────────────────────────────────────────
# Student numbering
# ─────────────────────────────────────────────────────────────────────────────

def get_student_number(username: str) -> int:
    """Return 1-based sequential number for a student (by registration order)."""
    ensure_setup()
    uname = username.strip().lower()
    students = [u for u in _read_all() if u.get("Role") == "student"]
    for i, u in enumerate(students, 1):
        if u.get("Username", "") == uname:
            return i
    # Check DEMO_USERS students
    demo_students = [u for u in DEMO_USERS if u[2] == "student"]
    for i, (du, _, _, _) in enumerate(demo_students, 1):
        if du.strip().lower() == uname:
            return i
    return 0


def get_student_display(user: dict) -> str:
    """Return 'S001 — Full Name' style display string for a student."""
    num = get_student_number(user.get("Username", ""))
    name = user.get("Full Name", user.get("Username", "Unknown"))
    if num:
        return f"S{num:03d} — {name}"
    return name


# ─────────────────────────────────────────────────────────────────────────────
# Persistent sessions  (in-memory; survives page reloads within same process)
# ─────────────────────────────────────────────────────────────────────────────

_SESSIONS: dict[str, str] = {}  # token → username


def create_persistent_session(username: str) -> str:
    """Create a session token for the given username. Returns the token."""
    token = str(uuid.uuid4())
    _SESSIONS[token] = username.strip().lower()
    return token


def restore_persistent_session(token: str) -> Optional[dict]:
    """Look up a session token and return the user dict, or None if not found."""
    if not token or token not in _SESSIONS:
        return None
    uname = _SESSIONS[token]
    # Check DEMO_USERS first
    for demo_uname, demo_pw, demo_role, demo_name in DEMO_USERS:
        if demo_uname.strip().lower() == uname:
            return {
                "User ID":       "demo",
                "Username":      uname,
                "Password Hash": _hash(demo_pw),
                "Role":          demo_role,
                "Full Name":     demo_name,
                "Created At":    "",
            }
    ensure_setup()
    for u in _read_all():
        if u.get("Username") == uname:
            return u
    return None


def delete_persistent_session(token: str) -> None:
    """Remove a session token."""
    _SESSIONS.pop(token, None)
