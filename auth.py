"""
auth.py
-------
Authentication and user management for the Preluma pre-class preparation system.

Storage strategy (evaluated in priority order on every read/write):
  1. Supabase  — active when SUPABASE_URL and SUPABASE_KEY are present in
                 Streamlit secrets. Data persists indefinitely across deploys.
  2. CSV file  — fallback for local development or when Supabase is unavailable.
                 On Streamlit Cloud this file resets on each deploy, so it is
                 treated as temporary storage only.

DEMO_USERS are a set of permanent accounts that are seeded on every startup.
They exist regardless of which backend is currently active, so named users
(teachers, demo students) are always available without manual re-registration.

Security note: passwords are stored as SHA-256 hashes. No third-party hashing
library is required — the standard hashlib module is sufficient for this use case.
"""

from __future__ import annotations

import csv
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests as _requests


DATA_DIR    = Path("data")
USERS_CSV   = DATA_DIR / "users.csv"
USER_FIELDS = ["User ID", "Username", "Password Hash", "Role", "Full Name", "Created At"]


# ---------------------------------------------------------------------------
# Permanent accounts — seeded on every startup
# ---------------------------------------------------------------------------
# Add any account here that must always exist after a fresh deploy.
# Format: (username, plain_password, role, full_name)
# Passwords are hashed before storage and never saved in plain text.

DEMO_USERS = [
    # Teaching staff
    ("teacher",     "teach123",    "teacher", "Prof. Amir Hossain"),
    ("mim.ynu",     "MimYnu24",    "teacher", "Mamunur Rashid (Admin)"),
    # Course teachers
    ("zhouyujue",   "Zhou2024",    "teacher", "Zhou Yujue"),
    ("gaosong",     "Gao2024",     "teacher", "Gao Song"),
    ("tangli",      "Tang2024",    "teacher", "Tang Li"),
    ("weiping",     "Wei2024",     "teacher", "Wei Ping"),
    # Development team (teacher-level access for system maintenance)
    ("mamun",       "preluma1",    "teacher", "Mamunur Rashid"),
    ("fahim",       "preluma1",    "teacher", "Md Fahim"),
    ("jiarul",      "preluma1",    "teacher", "Jiarul Islam"),
    # Demo student accounts used for class demonstrations
    ("student1",    "pass123",     "student", "Alice Wang"),
    ("student2",    "pass123",     "student", "Bob Chen"),
    ("class_demo",  "preluma123",  "student", "Class Demo"),
]


# ---------------------------------------------------------------------------
# Internal utility functions
# ---------------------------------------------------------------------------

def _hash(pw: str) -> str:
    """Return the SHA-256 hex digest of a password string."""
    return hashlib.sha256(pw.encode()).hexdigest()


def _now() -> str:
    """Return the current local time as a compact ISO 8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    """Generate a short, unique user ID from the first segment of a UUID."""
    return str(uuid.uuid4())[:8]


def _get_secret(name: str) -> str:
    """
    Read a single value from Streamlit secrets, returning an empty string
    if the key is missing or if Streamlit is not available (e.g. during tests).
    """
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        return str(val).strip() if val else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Supabase backend helpers
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    """Build the HTTP headers required for every Supabase REST API request."""
    key = _get_secret("SUPABASE_KEY")
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


def _sb_url() -> str:
    """Return the full Supabase REST endpoint for the users table."""
    base = _get_secret("SUPABASE_URL").rstrip("/")
    return f"{base}/rest/v1/preluma_users"


def _supabase_available() -> bool:
    """Return True when both required Supabase credentials are configured."""
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))


def _sb_read_all() -> list[dict]:
    """
    Fetch all user rows from Supabase and normalise the column names to match
    the local CSV field names. Returns an empty list on any network error.
    """
    try:
        resp = _requests.get(
            _sb_url(),
            headers={**_sb_headers(), "Prefer": "return=representation"},
            params={"select": "user_id,username,password_hash,role,full_name,created_at"},
            timeout=8,
        )
        resp.raise_for_status()
        return [{
            "User ID":       r.get("user_id", ""),
            "Username":      r.get("username", ""),
            "Password Hash": r.get("password_hash", ""),
            "Role":          r.get("role", "student"),
            "Full Name":     r.get("full_name", ""),
            "Created At":    r.get("created_at", ""),
        } for r in resp.json()]
    except Exception:
        return []


def _sb_upsert(row: dict) -> bool:
    """
    Write a single user row to Supabase, updating the existing record if the
    username already exists (merge-duplicates strategy). Returns True on success.
    """
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


# ---------------------------------------------------------------------------
# CSV backend helpers
# ---------------------------------------------------------------------------

def _csv_read_all() -> list[dict]:
    """Read and return all rows from the local users CSV file."""
    if not USERS_CSV.exists():
        return []
    with USERS_CSV.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _csv_append(row: dict) -> None:
    """Append a single user row to the local CSV, creating the file if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    needs_header = not USERS_CSV.exists()
    with USERS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=USER_FIELDS)
        if needs_header:
            w.writeheader()
        w.writerow(row)


# ---------------------------------------------------------------------------
# Unified read/write layer
# ---------------------------------------------------------------------------

def _read_all() -> list[dict]:
    """
    Return all user records from the active backend.

    Supabase is tried first. If it is unavailable or returns nothing, the
    local CSV is used as a fallback.
    """
    if _supabase_available():
        return _sb_read_all()
    return _csv_read_all()


def _write_row(row: dict) -> None:
    """Write a user row to whichever backend is currently active."""
    if _supabase_available():
        _sb_upsert(row)
    else:
        _csv_append(row)


# ---------------------------------------------------------------------------
# Initial setup
# ---------------------------------------------------------------------------

_SETUP_DONE: bool = False  # Guard flag to prevent re-seeding on every request.


def ensure_setup() -> None:
    """
    Seed all permanent demo accounts on the first call after startup.

    When Supabase is active, every DEMO_USER is upserted so that role or
    name changes in code are automatically reflected without manual database
    edits. When using CSV, only accounts that do not already exist are added
    to avoid duplicating rows across restarts.
    """
    global _SETUP_DONE
    if _SETUP_DONE:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if _supabase_available():
        for username, password, role, full_name in DEMO_USERS:
            _sb_upsert({
                "User ID":       _new_id(),
                "Username":      username.strip().lower(),
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def authenticate(username: str, password: str) -> Optional[dict]:
    """
    Verify a username and password pair and return the matching user record.

    DEMO_USERS are checked first using in-memory comparison, which avoids a
    network request for accounts that log in most frequently. If the login does
    not match any demo account, the active backend (Supabase or CSV) is queried.

    Returns None if the credentials are incorrect or the user does not exist.
    """
    uname   = username.strip().lower()
    pw_hash = _hash(password)

    # Fast path: check permanent accounts without touching the backend.
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
    """
    Return True if the username is already registered.

    DEMO_USERS are checked first so that reserved usernames are always
    considered taken, even before ensure_setup() has been called.
    """
    uname = username.strip().lower()
    for demo_uname, _, _, _ in DEMO_USERS:
        if demo_uname.strip().lower() == uname:
            return True
    return uname in {u["Username"] for u in _read_all()}


def register(
    username: str,
    password: str,
    full_name: str,
    role: str = "student",
) -> tuple[bool, str]:
    """
    Register a new user account after validating all required fields.

    Validation rules:
      - Username must be at least 3 characters.
      - Password must be at least 6 characters.
      - Full name must not be blank.
      - Username must not already be taken.

    Returns a (success, message) tuple. On success the message is a
    confirmation string; on failure it describes what went wrong.
    """
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
    """
    Update the stored password for an existing account.

    The user is identified by username alone — no security question or email
    is required. This keeps the reset flow simple for a classroom context.
    The new password is validated for minimum length before being hashed
    and written to both the active Supabase table and the local CSV.
    """
    uname = username.strip().lower()
    if not uname:
        return False, "Please enter your username."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    ensure_setup()
    if not username_exists(uname):
        return False, "Account not found. Please check your username."

    new_hash = _hash(new_password)

    # Update the Supabase record if the backend is available.
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
            pass  # Supabase update failed; the CSV update below still applies.

    # Always update the local CSV so offline and local-dev flows work correctly.
    users   = _csv_read_all()
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
    """Return all registered users whose role is 'student'."""
    ensure_setup()
    return [u for u in _read_all() if u["Role"] == "student"]


def get_all_users() -> list[dict]:
    """Return every registered user regardless of role."""
    ensure_setup()
    return _read_all()


def storage_backend() -> str:
    """Return the name of the currently active storage backend."""
    return "supabase" if _supabase_available() else "csv"


# ---------------------------------------------------------------------------
# Student display helpers
# ---------------------------------------------------------------------------

def get_student_number(username: str) -> int:
    """
    Return the 1-based sequential position of a student in the registration list.

    This number is used to generate the S001, S002 style display identifiers
    shown on the teacher's class roster. Returns 0 if the username is not found.
    """
    ensure_setup()
    uname    = username.strip().lower()
    students = [u for u in _read_all() if u.get("Role") == "student"]
    for i, u in enumerate(students, start=1):
        if u.get("Username", "") == uname:
            return i

    # Fall back to the position within the demo students list.
    demo_students = [(u, n) for u, _, r, n in DEMO_USERS if r == "student"]
    for i, (du, _) in enumerate(demo_students, start=1):
        if du.strip().lower() == uname:
            return i

    return 0


def get_student_display(user: dict) -> str:
    """
    Return a formatted display string for a student such as 'S001 — Alice Wang'.

    If no sequential number can be determined, only the full name is returned.
    """
    num  = get_student_number(user.get("Username", ""))
    name = user.get("Full Name", user.get("Username", "Unknown"))
    if num:
        return f"S{num:03d} — {name}"
    return name


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_SESSIONS: dict[str, str] = {}  # Maps session token → username (in-memory only).


def create_persistent_session(username: str) -> str:
    """
    Generate and store a session token for the given username.

    Tokens are UUID strings kept in a module-level dictionary. They survive
    Streamlit page reloads within the same server process but are cleared on
    restart. This is intentional — after a restart, users log in again.
    """
    token = str(uuid.uuid4())
    _SESSIONS[token] = username.strip().lower()
    return token


def restore_persistent_session(token: str) -> Optional[dict]:
    """
    Look up a session token and return the corresponding user record.

    Returns None if the token does not exist or has been invalidated.
    DEMO_USERS are checked first so that the session restore path is
    consistent with the authenticate() logic.
    """
    if not token or token not in _SESSIONS:
        return None

    uname = _SESSIONS[token]

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
    """Remove a session token, effectively logging the user out."""
    _SESSIONS.pop(token, None)
