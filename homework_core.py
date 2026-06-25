"""
homework_core.py
----------------
Homework management layer for the Preluma pre-class preparation system.

This module handles the complete lifecycle of a homework assignment:
  - Creation: saving the assignment record and its questions to CSV/Supabase
  - Notification: alerting the right students when new work is assigned
  - Submission: receiving student answers, scoring them, and logging mistakes
  - Reporting: generating per-homework statistics for the teacher dashboard

All persistent data is stored in CSV files inside the /data directory.
Each write operation immediately calls backup_csv() so that Supabase receives
the latest data and the app survives a server restart without losing records.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from storage_core import backup_csv, restore_csv


# ---------------------------------------------------------------------------
# File paths and column schemas
# ---------------------------------------------------------------------------

DATA_DIR          = Path("data")
HOMEWORK_CSV      = DATA_DIR / "homework.csv"
QUESTIONS_CSV     = DATA_DIR / "homework_questions.csv"
SUBMISSIONS_CSV   = DATA_DIR / "homework_submissions.csv"
MISTAKES_CSV      = DATA_DIR / "student_mistakes.csv"
NOTIFICATIONS_CSV = DATA_DIR / "notifications.csv"

# These field lists also define column order inside each CSV file.
HOMEWORK_FIELDS = [
    "Homework ID", "Title", "Topic", "Instructions", "Due Date",
    "Difficulty", "Assigned To", "Created By", "Created At", "Published", "Attachment",
]
QUESTION_FIELDS = [
    "Homework ID", "Question ID", "Question", "Option A", "Option B",
    "Option C", "Option D", "Correct Answer", "Concept", "Explanation", "Marks",
]
SUBMISSION_FIELDS = [
    "Submission ID", "Homework ID", "Student", "Score", "Total",
    "Percentage", "Attempt", "Submitted At", "Status",
]
MISTAKE_FIELDS = [
    "Submission ID", "Homework ID", "Student", "Question ID", "Question",
    "Student Answer", "Correct Answer", "Weak Concept", "Explanation", "Created At",
]
NOTIFICATION_FIELDS = [
    "Notification ID", "Student", "Type", "Title", "Message",
    "Reference ID", "Is Read", "Created At",
]

# Mapping used by _read_rows() to look up the field list for any known file.
_CSV_FIELDS: dict[Path, list[str]] = {
    HOMEWORK_CSV:      HOMEWORK_FIELDS,
    QUESTIONS_CSV:     QUESTION_FIELDS,
    SUBMISSIONS_CSV:   SUBMISSION_FIELDS,
    MISTAKES_CSV:      MISTAKE_FIELDS,
    NOTIFICATIONS_CSV: NOTIFICATION_FIELDS,
}


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def now_text() -> str:
    """Return the current local time as a compact ISO 8601 string."""
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Low-level CSV helpers
# ---------------------------------------------------------------------------

def _ensure_csv(path: Path, fields: list[str]) -> None:
    """
    Guarantee that a CSV file exists and has the correct header row.

    The function first attempts to restore the file from Supabase. This means
    that on a fresh Streamlit Cloud deploy, all historical records reappear
    automatically rather than starting from an empty file.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if not restore_csv(path, fields):
            # Supabase had no data; create a local empty file with the header.
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, fieldnames=fields).writeheader()


def ensure_homework_files() -> None:
    """Ensure all five homework-related CSV files exist before any read or write."""
    _ensure_csv(HOMEWORK_CSV,      HOMEWORK_FIELDS)
    _ensure_csv(QUESTIONS_CSV,     QUESTION_FIELDS)
    _ensure_csv(SUBMISSIONS_CSV,   SUBMISSION_FIELDS)
    _ensure_csv(MISTAKES_CSV,      MISTAKE_FIELDS)
    _ensure_csv(NOTIFICATIONS_CSV, NOTIFICATION_FIELDS)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    """
    Read all rows from a CSV file and return them as a list of dictionaries.

    If the file does not exist locally, the function tries to restore it from
    Supabase before giving up and returning an empty list. This handles the
    case where a deploy cleared the local filesystem.
    """
    if not path.exists():
        fields = _CSV_FIELDS.get(path, [])
        if fields:
            restore_csv(path, fields)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _append_row(path: Path, fields: list[str], row: dict[str, Any]) -> None:
    """
    Append a single row to a CSV file and immediately push the updated file
    to Supabase so data is not lost if the server restarts.
    """
    _ensure_csv(path, fields)
    # Only write the fields that are expected — extra keys are silently ignored.
    clean = {field: row.get(field, "") for field in fields}
    with path.open("a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=fields).writerow(clean)
    backup_csv(path)


def _next_id(path: Path, field: str) -> int:
    """
    Return the next available integer ID for a given column.

    The function scans every existing row and returns max(existing_ids) + 1.
    Starting from zero is handled gracefully: if the file is empty the first
    call returns 1.
    """
    maximum = 0
    for row in _read_rows(path):
        try:
            value = int(row.get(field, 0))
            if value > maximum:
                maximum = value
        except (TypeError, ValueError):
            continue
    return maximum + 1


# ---------------------------------------------------------------------------
# Homework creation
# ---------------------------------------------------------------------------

def create_homework(
    title: str,
    topic: str,
    instructions: str,
    due_date: str,
    difficulty: str,
    assigned_to: str,
    created_by: str,
    questions: list[dict[str, Any]],
    attachment: str = "",
) -> tuple[int, int]:
    """
    Create a new homework assignment and save it with its questions.

    The function writes one row to HOMEWORK_CSV, one row per question to
    QUESTIONS_CSV, and one notification row per target student. The same
    homework_id is returned twice so callers that unpack both values remain
    compatible.

    Parameters
    ----------
    title        : Human-readable name shown in the student interface.
    topic        : The academic topic the homework covers.
    instructions : Free-text guidance for students, displayed above the questions.
    due_date     : Deadline text (e.g. "Friday 8:00 PM").
    difficulty   : One of Beginner / Intermediate / Advanced.
    assigned_to  : Comma-separated student names, or "All Students".
    created_by   : Teacher username who created the assignment.
    questions    : List of question dicts with keys: question, options, answer,
                   concept, explanation, marks.
    attachment   : Optional URL or filename for supplementary material.

    Returns
    -------
    A tuple (homework_id, homework_id) for backward compatibility.
    """
    ensure_homework_files()
    homework_id = _next_id(HOMEWORK_CSV, "Homework ID")

    _append_row(HOMEWORK_CSV, HOMEWORK_FIELDS, {
        "Homework ID": homework_id,
        "Title":        title,
        "Topic":        topic,
        "Instructions": instructions,
        "Due Date":     due_date,
        "Difficulty":   difficulty,
        "Assigned To":  assigned_to or "All Students",
        "Created By":   created_by,
        "Created At":   now_text(),
        "Published":    "Yes",
        "Attachment":   attachment or "",
    })

    # Each question in the list becomes its own row, numbered from 1.
    for question_id, question in enumerate(questions, start=1):
        opts = question.get("options", ["", "", "", ""])
        _append_row(QUESTIONS_CSV, QUESTION_FIELDS, {
            "Homework ID":    homework_id,
            "Question ID":    question_id,
            "Question":       question.get("question", ""),
            "Option A":       opts[0] if len(opts) > 0 else "",
            "Option B":       opts[1] if len(opts) > 1 else "",
            "Option C":       opts[2] if len(opts) > 2 else "",
            "Option D":       opts[3] if len(opts) > 3 else "",
            "Correct Answer": question.get("answer", ""),
            "Concept":        question.get("concept", topic),
            "Explanation":    question.get("explanation", ""),
            "Marks":          question.get("marks", 1),
        })

    # Notify each target student individually so the badge count is accurate.
    targets = [name.strip() for name in assigned_to.split(",") if name.strip()]
    if not targets:
        targets = ["All Students"]
    for student in targets:
        create_notification(
            student=student,
            notification_type="Homework",
            title=f"New homework: {title}",
            message=f"{topic} homework is due on {due_date}.",
            reference_id=homework_id,
        )

    return homework_id, homework_id


# ---------------------------------------------------------------------------
# Notification management
# ---------------------------------------------------------------------------

def create_notification(
    student: str,
    notification_type: str,
    title: str,
    message: str,
    reference_id: int | str,
) -> int:
    """
    Save a new notification for a student and return its ID.

    Notifications are always created with Is Read = "No" so they appear in
    the student's unread badge count until the student visits the page.
    The student field may be a specific name or "All Students" to target
    every student in the class.
    """
    ensure_homework_files()
    notification_id = _next_id(NOTIFICATIONS_CSV, "Notification ID")
    _append_row(NOTIFICATIONS_CSV, NOTIFICATION_FIELDS, {
        "Notification ID": notification_id,
        "Student":         student,
        "Type":            notification_type,
        "Title":           title,
        "Message":         message,
        "Reference ID":    reference_id,
        "Is Read":         "No",
        "Created At":      now_text(),
    })
    return notification_id


def notifications_for_student(
    student: str,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Return all notifications that belong to a specific student.

    Matching is case-insensitive. A notification is included if its Student
    field equals the student's name or equals "all students" (broadcast).
    When unread_only is True, only notifications with Is Read = "No" are
    returned — useful for the sidebar badge counter.
    """
    ensure_homework_files()
    student_key = student.strip().casefold()
    output = []
    for row in _read_rows(NOTIFICATIONS_CSV):
        target = str(row.get("Student", "")).strip().casefold()
        if target in ("all students", student_key):
            if not unread_only or row.get("Is Read") == "No":
                output.append(row)
    return output


def mark_notifications_read(student: str) -> None:
    """
    Set Is Read = "Yes" on every unread notification for a student.

    This is called when the student opens the notifications page so the badge
    counter resets to zero. The full file is rewritten because CSV does not
    support in-place row updates.
    """
    ensure_homework_files()
    student_key = student.strip().casefold()
    rows    = _read_rows(NOTIFICATIONS_CSV)
    changed = False

    for row in rows:
        target = str(row.get("Student", "")).strip().casefold()
        if target in ("all students", student_key) and row.get("Is Read") == "No":
            row["Is Read"] = "Yes"
            changed = True

    if changed:
        fieldnames = list(rows[0].keys()) if rows else NOTIFICATION_FIELDS
        with open(NOTIFICATIONS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        backup_csv(NOTIFICATIONS_CSV)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_homework() -> list[dict[str, Any]]:
    """Return every homework assignment in the system."""
    ensure_homework_files()
    return _read_rows(HOMEWORK_CSV)


def load_questions(homework_id: int | str) -> list[dict[str, Any]]:
    """
    Return all questions for a specific homework assignment.

    Each returned row gains an extra 'Options' key holding a list of the four
    answer choices so the rendering code does not need to reassemble them.
    """
    ensure_homework_files()
    target = str(homework_id)
    rows   = []
    for row in _read_rows(QUESTIONS_CSV):
        if str(row.get("Homework ID")) == target:
            row["Options"] = [
                row.get("Option A", ""),
                row.get("Option B", ""),
                row.get("Option C", ""),
                row.get("Option D", ""),
            ]
            rows.append(row)
    return rows


def homework_for_student(student: str) -> list[dict[str, Any]]:
    """
    Return every homework assignment that a specific student should complete.

    An assignment is included if the student is named in the Assigned To field
    or if the field contains "All Students". Comparison is case-insensitive.
    """
    student_key = student.strip().casefold()
    output = []
    for row in load_homework():
        assigned = str(row.get("Assigned To", "All Students"))
        targets  = [v.strip().casefold() for v in assigned.split(",")]
        if "all students" in targets or student_key in targets:
            output.append(row)
    return output


def load_submissions(homework_id: int | str | None = None) -> list[dict[str, Any]]:
    """
    Return submission records, optionally filtered to one homework assignment.

    Passing None returns every submission in the system, which is useful for
    generating class-wide analytics on the teacher dashboard.
    """
    ensure_homework_files()
    rows = _read_rows(SUBMISSIONS_CSV)
    if homework_id is None:
        return rows
    return [row for row in rows if str(row.get("Homework ID")) == str(homework_id)]


def load_student_mistakes(student: str) -> list[dict[str, Any]]:
    """Return all mistake records for a specific student."""
    ensure_homework_files()
    key = student.strip().casefold()
    return [
        row for row in _read_rows(MISTAKES_CSV)
        if str(row.get("Student", "")).strip().casefold() == key
    ]


def load_all_mistakes() -> list[dict[str, Any]]:
    """
    Load every row from the mistakes CSV in a single read.

    Use this in bulk loops (e.g. the teacher analytics page) to avoid
    reopening the file once per student, which becomes slow with many students.
    """
    ensure_homework_files()
    return _read_rows(MISTAKES_CSV)


# ---------------------------------------------------------------------------
# Submission processing
# ---------------------------------------------------------------------------

def submit_homework(
    homework_id: int | str,
    student: str,
    answers: dict[int, str],
) -> dict[str, Any]:
    """
    Grade a student's homework submission and record the results.

    For each question, the student's chosen answer is compared to the stored
    correct answer. Wrong answers are individually logged to the mistakes file
    so the teacher can identify which concepts need review.

    The attempt counter is derived from the existing submission count for this
    student on this homework, so it is always accurate even after reloads.

    Parameters
    ----------
    homework_id : ID of the homework assignment being submitted.
    student     : Full name of the student submitting.
    answers     : Mapping of {question_id: chosen_option_text}.

    Returns
    -------
    A summary dict with keys: submission_id, score, total, percentage,
    attempt, details (list of per-question results), mistakes (list of
    wrong-answer records).
    """
    questions = load_questions(homework_id)

    # Count previous attempts for this student to set the attempt number correctly.
    previous_attempts = sum(
        1 for row in _read_rows(SUBMISSIONS_CSV)
        if str(row.get("Homework ID")) == str(homework_id)
        and str(row.get("Student", "")).strip().casefold() == student.strip().casefold()
    )
    attempt       = previous_attempts + 1
    submission_id = _next_id(SUBMISSIONS_CSV, "Submission ID")

    score   = 0
    total   = 0
    details = []
    mistakes: list[dict[str, Any]] = []

    for question in questions:
        question_id    = int(question.get("Question ID", 0))
        marks          = int(float(question.get("Marks", 1) or 1))
        total         += marks
        chosen         = (answers.get(question_id, "") or "").strip()
        correct_answer = (question.get("Correct Answer", "") or "").strip()
        is_correct     = (chosen == correct_answer)

        if is_correct:
            score += marks
        else:
            mistake_row = {
                "Submission ID": submission_id,
                "Homework ID":   homework_id,
                "Student":       student,
                "Question ID":   question_id,
                "Question":      question.get("Question", ""),
                "Student Answer":chosen,
                "Correct Answer":correct_answer,
                "Weak Concept":  question.get("Concept", ""),
                "Explanation":   question.get("Explanation", ""),
                "Created At":    now_text(),
            }
            _append_row(MISTAKES_CSV, MISTAKE_FIELDS, mistake_row)
            mistakes.append(mistake_row)

        details.append({
            "question_id":   question_id,
            "question":      question.get("Question", ""),
            "chosen":        chosen,
            "correct_answer":correct_answer,
            "correct":       is_correct,
            "concept":       question.get("Concept", ""),
            "explanation":   question.get("Explanation", ""),
            "marks":         marks,
        })

    percentage = round((score / total) * 100, 1) if total else 0.0

    _append_row(SUBMISSIONS_CSV, SUBMISSION_FIELDS, {
        "Submission ID": submission_id,
        "Homework ID":   homework_id,
        "Student":       student,
        "Score":         score,
        "Total":         total,
        "Percentage":    percentage,
        "Attempt":       attempt,
        "Submitted At":  now_text(),
        "Status":        "Submitted",
    })

    return {
        "submission_id": submission_id,
        "score":         score,
        "total":         total,
        "percentage":    percentage,
        "attempt":       attempt,
        "details":       details,
        "mistakes":      mistakes,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def homework_overview(homework_id: int | str) -> dict[str, Any]:
    """
    Compute summary statistics for one homework assignment.

    Returns the number of submissions, unique students, average/highest/lowest
    percentage, and the concept that produced the most mistakes. This data
    powers the teacher's results panel and helps identify which topic needs
    additional class time.
    """
    submissions = load_submissions(homework_id)
    percentages: list[float] = []
    students: set[str] = set()

    for row in submissions:
        students.add(str(row.get("Student", "")))
        try:
            percentages.append(float(row.get("Percentage", 0.0)))
        except (TypeError, ValueError):
            percentages.append(0.0)

    average = sum(percentages) / len(percentages) if percentages else 0.0
    highest = max(percentages) if percentages else 0.0
    lowest  = min(percentages) if percentages else 0.0

    # Tally mistakes by concept to find the most common weak area.
    concept_counts: dict[str, int] = {}
    for row in _read_rows(MISTAKES_CSV):
        if str(row.get("Homework ID")) == str(homework_id):
            concept = str(row.get("Weak Concept", "Unknown") or "Unknown")
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

    common_concept = "None"
    common_count   = 0
    for concept, count in concept_counts.items():
        if count > common_count:
            common_concept = concept
            common_count   = count

    return {
        "submissions":         len(submissions),
        "unique_students":     len(students),
        "average":             round(average, 1),
        "highest":             round(highest, 1),
        "lowest":              round(lowest, 1),
        "common_weak_concept": common_concept,
        "common_weak_count":   common_count,
        "submission_rows":     submissions,
    }


# ---------------------------------------------------------------------------
# Demo data seeder
# ---------------------------------------------------------------------------

def seed_homework_demo() -> None:
    """
    Insert a starter homework assignment if the system has no data yet.

    This runs on first launch so teachers and students see a working example
    immediately, without needing to create a test assignment manually.
    The function does nothing if any homework already exists.
    """
    ensure_homework_files()
    if load_homework():
        return

    demo_questions = [
        {
            "question": "What is the main job of a neural network?",
            "options":  [
                "Learn patterns from examples",
                "Store files only",
                "Replace every human decision",
                "Increase internet speed",
            ],
            "answer":      "Learn patterns from examples",
            "concept":     "Neural network purpose",
            "explanation": "A neural network learns patterns from training examples and uses them to make predictions.",
            "marks":       1,
        },
        {
            "question": "What does a weight represent in a neural network?",
            "options":  [
                "The physical weight of a computer",
                "The importance of a connection",
                "The number of users",
                "The file size",
            ],
            "answer":      "The importance of a connection",
            "concept":     "Weights",
            "explanation": "A weight controls how strongly one value influences the next part of the network.",
            "marks":       1,
        },
        {
            "question": "Which example best describes training?",
            "options":  [
                "Learning from many labelled examples",
                "Turning off the computer",
                "Deleting all data",
                "Only reading one answer",
            ],
            "answer":      "Learning from many labelled examples",
            "concept":     "Training",
            "explanation": "Training means adjusting the model by learning from examples.",
            "marks":       1,
        },
    ]

    create_homework(
        title       ="Neural Network Foundations",
        topic       ="Neural Network",
        instructions="Review the basic concepts and complete the three questions.",
        due_date    ="Friday 8:00 PM",
        difficulty  ="Beginner",
        assigned_to ="All Students",
        created_by  ="Teacher Demo",
        questions   =demo_questions,
    )
