from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from storage_core import backup_csv, restore_csv

DATA_DIR = Path("data")
HOMEWORK_CSV = DATA_DIR / "homework.csv"
QUESTIONS_CSV = DATA_DIR / "homework_questions.csv"
SUBMISSIONS_CSV = DATA_DIR / "homework_submissions.csv"
MISTAKES_CSV = DATA_DIR / "student_mistakes.csv"
NOTIFICATIONS_CSV = DATA_DIR / "notifications.csv"

HOMEWORK_FIELDS = [
    "Homework ID", "Title", "Topic", "Instructions", "Due Date",
    "Difficulty", "Assigned To", "Created By", "Created At", "Published", "Attachment"
]
QUESTION_FIELDS = [
    "Homework ID", "Question ID", "Question", "Option A", "Option B",
    "Option C", "Option D", "Correct Answer", "Concept", "Explanation", "Marks"
]
SUBMISSION_FIELDS = [
    "Submission ID", "Homework ID", "Student", "Score", "Total",
    "Percentage", "Attempt", "Submitted At", "Status"
]
MISTAKE_FIELDS = [
    "Submission ID", "Homework ID", "Student", "Question ID", "Question",
    "Student Answer", "Correct Answer", "Weak Concept", "Explanation", "Created At"
]
NOTIFICATION_FIELDS = [
    "Notification ID", "Student", "Type", "Title", "Message",
    "Reference ID", "Is Read", "Created At"
]


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


_CSV_FIELDS = {
    HOMEWORK_CSV: HOMEWORK_FIELDS,
    QUESTIONS_CSV: QUESTION_FIELDS,
    SUBMISSIONS_CSV: SUBMISSION_FIELDS,
    MISTAKES_CSV: MISTAKE_FIELDS,
    NOTIFICATIONS_CSV: NOTIFICATION_FIELDS,
}

def _ensure_csv(path: Path, fields: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Try Supabase restore first
        if not restore_csv(path, fields):
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, fieldnames=fields).writeheader()


def ensure_homework_files() -> None:
    _ensure_csv(HOMEWORK_CSV, HOMEWORK_FIELDS)
    _ensure_csv(QUESTIONS_CSV, QUESTION_FIELDS)
    _ensure_csv(SUBMISSIONS_CSV, SUBMISSION_FIELDS)
    _ensure_csv(MISTAKES_CSV, MISTAKE_FIELDS)
    _ensure_csv(NOTIFICATIONS_CSV, NOTIFICATION_FIELDS)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        fields = _CSV_FIELDS.get(path, [])
        if fields:
            restore_csv(path, fields)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _append_row(path: Path, fields: list[str], row: dict[str, Any]) -> None:
    _ensure_csv(path, fields)
    clean = {field: row.get(field, "") for field in fields}
    with path.open("a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=fields).writerow(clean)
    backup_csv(path)  # persist to Supabase immediately


def _next_id(path: Path, field: str) -> int:
    maximum = 0
    for row in _read_rows(path):
        try:
            value = int(row.get(field, 0))
            if value > maximum:
                maximum = value
        except (TypeError, ValueError):
            continue
    return maximum + 1


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
) -> int:
    ensure_homework_files()
    homework_id = _next_id(HOMEWORK_CSV, "Homework ID")
    _append_row(HOMEWORK_CSV, HOMEWORK_FIELDS, {
        "Homework ID": homework_id,
        "Title": title,
        "Topic": topic,
        "Instructions": instructions,
        "Due Date": due_date,
        "Difficulty": difficulty,
        "Assigned To": assigned_to or "All Students",
        "Created By": created_by,
        "Created At": now_text(),
        "Published": "Yes",
        "Attachment": attachment or "",
    })

    question_id = 1
    for question in questions:
        _append_row(QUESTIONS_CSV, QUESTION_FIELDS, {
            "Homework ID": homework_id,
            "Question ID": question_id,
            "Question": question.get("question", ""),
            "Option A": question.get("options", ["", "", "", ""])[0],
            "Option B": question.get("options", ["", "", "", ""])[1],
            "Option C": question.get("options", ["", "", "", ""])[2],
            "Option D": question.get("options", ["", "", "", ""])[3],
            "Correct Answer": question.get("answer", ""),
            "Concept": question.get("concept", topic),
            "Explanation": question.get("explanation", ""),
            "Marks": question.get("marks", 1),
        })
        question_id += 1

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


def create_notification(
    student: str,
    notification_type: str,
    title: str,
    message: str,
    reference_id: int | str,
) -> int:
    ensure_homework_files()
    notification_id = _next_id(NOTIFICATIONS_CSV, "Notification ID")
    _append_row(NOTIFICATIONS_CSV, NOTIFICATION_FIELDS, {
        "Notification ID": notification_id,
        "Student": student,
        "Type": notification_type,
        "Title": title,
        "Message": message,
        "Reference ID": reference_id,
        "Is Read": "No",
        "Created At": now_text(),
    })
    return notification_id


def load_homework() -> list[dict[str, Any]]:
    ensure_homework_files()
    return _read_rows(HOMEWORK_CSV)


def load_questions(homework_id: int | str) -> list[dict[str, Any]]:
    ensure_homework_files()
    target = str(homework_id)
    rows = []
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
    student_key = student.strip().casefold()
    output = []
    for row in load_homework():
        assigned = str(row.get("Assigned To", "All Students"))
        targets = [value.strip().casefold() for value in assigned.split(",")]
        if "all students" in targets or student_key in targets:
            output.append(row)
    return output


def notifications_for_student(student: str, unread_only: bool = False) -> list[dict[str, Any]]:
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
    """Mark all notifications for this student as read in the CSV."""
    ensure_homework_files()
    student_key = student.strip().casefold()
    rows = _read_rows(NOTIFICATIONS_CSV)
    changed = False
    for row in rows:
        target = str(row.get("Student", "")).strip().casefold()
        if target in ("all students", student_key) and row.get("Is Read") == "No":
            row["Is Read"] = "Yes"
            changed = True
    if changed:
        fieldnames = list(rows[0].keys()) if rows else ["Notification ID", "Student", "Title", "Message", "Is Read", "Created At"]
        with open(NOTIFICATIONS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        backup_csv(NOTIFICATIONS_CSV)


def submit_homework(
    homework_id: int | str,
    student: str,
    answers: dict[int, str],
) -> dict[str, Any]:
    questions = load_questions(homework_id)
    submission_id = _next_id(SUBMISSIONS_CSV, "Submission ID")

    score = 0
    total = 0
    details = []
    mistakes = []

    previous_attempts = 0
    for row in _read_rows(SUBMISSIONS_CSV):
        if str(row.get("Homework ID")) == str(homework_id) and \
           str(row.get("Student", "")).strip().casefold() == student.strip().casefold():
            previous_attempts += 1
    attempt = previous_attempts + 1

    for question in questions:
        question_id = int(question.get("Question ID", 0))
        marks = int(float(question.get("Marks", 1) or 1))
        total += marks
        chosen = answers.get(question_id, "") or ""
        correct_answer = question.get("Correct Answer", "") or ""
        correct = chosen.strip() == correct_answer.strip()
        if correct:
            score += marks
        else:
            mistake = {
                "Submission ID": submission_id,
                "Homework ID": homework_id,
                "Student": student,
                "Question ID": question_id,
                "Question": question.get("Question", ""),
                "Student Answer": chosen,
                "Correct Answer": correct_answer,
                "Weak Concept": question.get("Concept", ""),
                "Explanation": question.get("Explanation", ""),
                "Created At": now_text(),
            }
            _append_row(MISTAKES_CSV, MISTAKE_FIELDS, mistake)
            mistakes.append(mistake)

        details.append({
            "question_id": question_id,
            "question": question.get("Question", ""),
            "chosen": chosen,
            "correct_answer": correct_answer,
            "correct": correct,
            "concept": question.get("Concept", ""),
            "explanation": question.get("Explanation", ""),
            "marks": marks,
        })

    percentage = round((score / total) * 100, 1) if total else 0.0
    _append_row(SUBMISSIONS_CSV, SUBMISSION_FIELDS, {
        "Submission ID": submission_id,
        "Homework ID": homework_id,
        "Student": student,
        "Score": score,
        "Total": total,
        "Percentage": percentage,
        "Attempt": attempt,
        "Submitted At": now_text(),
        "Status": "Submitted",
    })

    return {
        "submission_id": submission_id,
        "score": score,
        "total": total,
        "percentage": percentage,
        "attempt": attempt,
        "details": details,
        "mistakes": mistakes,
    }


def load_submissions(homework_id: int | str | None = None) -> list[dict[str, Any]]:
    ensure_homework_files()
    rows = _read_rows(SUBMISSIONS_CSV)
    if homework_id is None:
        return rows
    return [row for row in rows if str(row.get("Homework ID")) == str(homework_id)]


def load_student_mistakes(student: str) -> list[dict[str, Any]]:
    ensure_homework_files()
    key = student.strip().casefold()
    return [
        row for row in _read_rows(MISTAKES_CSV)
        if str(row.get("Student", "")).strip().casefold() == key
    ]


def load_all_mistakes() -> list[dict[str, Any]]:
    """Load every row from mistakes CSV in a single read — use this in bulk loops."""
    ensure_homework_files()
    return _read_rows(MISTAKES_CSV)


def homework_overview(homework_id: int | str) -> dict[str, Any]:
    submissions = load_submissions(homework_id)
    percentages = []
    students = set()
    for row in submissions:
        students.add(str(row.get("Student", "")))
        try:
            percentages.append(float(row.get("Percentage", 0.0)))
        except (TypeError, ValueError):
            percentages.append(0.0)

    average = sum(percentages) / len(percentages) if percentages else 0.0
    highest = max(percentages) if percentages else 0.0
    lowest = min(percentages) if percentages else 0.0

    concept_counts: dict[str, int] = {}
    for row in _read_rows(MISTAKES_CSV):
        if str(row.get("Homework ID")) == str(homework_id):
            concept = str(row.get("Weak Concept", "Unknown") or "Unknown")
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

    common_concept = "None"
    common_count = 0
    for concept, count in concept_counts.items():
        if count > common_count:
            common_concept = concept
            common_count = count

    return {
        "submissions": len(submissions),
        "unique_students": len(students),
        "average": round(average, 1),
        "highest": round(highest, 1),
        "lowest": round(lowest, 1),
        "common_weak_concept": common_concept,
        "common_weak_count": common_count,
        "submission_rows": submissions,
    }


def seed_homework_demo() -> None:
    ensure_homework_files()
    if load_homework():
        return
    questions = [
        {
            "question": "What is the main job of a neural network?",
            "options": [
                "Learn patterns from examples",
                "Store files only",
                "Replace every human decision",
                "Increase internet speed",
            ],
            "answer": "Learn patterns from examples",
            "concept": "Neural network purpose",
            "explanation": "A neural network learns patterns from training examples and uses them to make predictions.",
            "marks": 1,
        },
        {
            "question": "What does a weight represent in a neural network?",
            "options": [
                "The physical weight of a computer",
                "The importance of a connection",
                "The number of users",
                "The file size",
            ],
            "answer": "The importance of a connection",
            "concept": "Weights",
            "explanation": "A weight controls how strongly one value influences the next part of the network.",
            "marks": 1,
        },
        {
            "question": "Which example best describes training?",
            "options": [
                "Learning from many labelled examples",
                "Turning off the computer",
                "Deleting all data",
                "Only reading one answer",
            ],
            "answer": "Learning from many labelled examples",
            "concept": "Training",
            "explanation": "Training means adjusting the model by learning from examples.",
            "marks": 1,
        },
    ]
    create_homework(
        title="Neural Network Foundations",
        topic="Neural Network",
        instructions="Review the basic concepts and complete the three questions.",
        due_date="Friday 8:00 PM",
        difficulty="Beginner",
        assigned_to="All Students",
        created_by="Teacher Demo",
        questions=questions,
    )
