"""
models.py — Preluma Data Models
================================
Defines typed dataclass representations for the two core entities
produced by Preluma's algorithm pipeline:

  StudentRecord  — one row of student readiness data (mirrors students.csv)
  AnalysisResult — summary produced by Teacher Studio analytics

Using standard-library dataclasses only (no third-party dependencies).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StudentRecord:
    """
    Represents a single student readiness entry.

    Maps 1-to-1 with a row in data/students.csv.
    Used by algorithms_core.merge_sort_records() and binary_search_leftmost()
    to sort and search student data.

    Attributes
    ----------
    record_id    : Unique integer ID, assigned by storage_core.next_record_id()
    student      : Student display name
    topic        : Topic the student studied in the mission
    readiness    : Float 0–100 readiness score (quiz-derived)
    weak_skill   : Name of the concept the student answered wrong, or empty string
    quiz_score   : Raw number of correct answers
    quiz_total   : Total questions in the quiz
    lecture_time : ISO-8601 timestamp string when the record was created
    learning_mode: "Guided" or "Quick" — mission style chosen by the student
    created_at   : ISO-8601 timestamp string (alias of lecture_time for audit)
    """
    record_id: int
    student: str
    topic: str
    readiness: float
    weak_skill: str
    quiz_score: int
    quiz_total: int
    lecture_time: str
    learning_mode: str
    created_at: str

    @classmethod
    def from_csv_row(cls, row: dict) -> "StudentRecord":
        """
        Build a StudentRecord from a csv.DictReader row dict.

        Raises ValueError if required fields are missing or malformed.
        """
        try:
            return cls(
                record_id=int(row.get("record_id", 0)),
                student=str(row.get("student", "")).strip(),
                topic=str(row.get("topic", "")).strip(),
                readiness=float(row.get("readiness", 0.0)),
                weak_skill=str(row.get("weak_skill", "")).strip(),
                quiz_score=int(row.get("quiz_score", 0)),
                quiz_total=int(row.get("quiz_total", 0)),
                lecture_time=str(row.get("lecture_time", "")).strip(),
                learning_mode=str(row.get("learning_mode", "Guided")).strip(),
                created_at=str(row.get("created_at", "")).strip(),
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(f"StudentRecord.from_csv_row failed: {exc}") from exc

    def to_sort_key(self) -> float:
        """Return the numeric key used by Merge Sort (readiness, descending by convention)."""
        return self.readiness

    def __repr__(self) -> str:
        return (
            f"StudentRecord(id={self.record_id}, student={self.student!r}, "
            f"topic={self.topic!r}, readiness={self.readiness})"
        )


@dataclass
class AnalysisResult:
    """
    Summary statistics produced by Teacher Studio analytics.

    Populated by analytics_core functions and algorithms_core timing,
    then displayed in Teacher Studio and written to result.txt.

    Attributes
    ----------
    student_count         : Total number of student records analysed
    average_readiness     : Arithmetic mean of readiness scores (manual algorithm)
    lowest_readiness      : Minimum readiness in the dataset
    highest_readiness     : Maximum readiness in the dataset
    variance              : Population variance of readiness scores (manual algorithm)
    most_common_weak_skill: The concept most students struggled with (may be empty)
    merge_sort_elapsed_ns : Nanoseconds taken by Merge Sort (from perf_counter_ns)
    linear_search_elapsed_ns  : Nanoseconds taken by Linear Search
    binary_search_elapsed_ns  : Nanoseconds taken by Binary Search
    sorted_records        : List of StudentRecord sorted by readiness (desc)
    """
    student_count: int
    average_readiness: float
    lowest_readiness: float
    highest_readiness: float
    variance: float
    most_common_weak_skill: str
    merge_sort_elapsed_ns: int = 0
    linear_search_elapsed_ns: int = 0
    binary_search_elapsed_ns: int = 0
    sorted_records: list = field(default_factory=list)

    def merge_sort_elapsed_ms(self) -> float:
        """Return Merge Sort elapsed time in milliseconds (2 decimal places)."""
        return round(self.merge_sort_elapsed_ns / 1_000_000, 2)

    def linear_search_elapsed_ms(self) -> float:
        """Return Linear Search elapsed time in milliseconds."""
        return round(self.linear_search_elapsed_ns / 1_000_000, 2)

    def binary_search_elapsed_ms(self) -> float:
        """Return Binary Search elapsed time in milliseconds."""
        return round(self.binary_search_elapsed_ns / 1_000_000, 2)

    def summary_lines(self) -> list[str]:
        """
        Return a list of human-readable summary lines suitable for result.txt.
        """
        return [
            f"Student count       : {self.student_count}",
            f"Average readiness   : {self.average_readiness:.2f}",
            f"Highest readiness   : {self.highest_readiness:.2f}",
            f"Lowest readiness    : {self.lowest_readiness:.2f}",
            f"Variance            : {self.variance:.2f}",
            f"Most common weak    : {self.most_common_weak_skill or 'None'}",
            f"Merge Sort time     : {self.merge_sort_elapsed_ns} ns  "
            f"({self.merge_sort_elapsed_ms()} ms)",
            f"Linear Search time  : {self.linear_search_elapsed_ns} ns  "
            f"({self.linear_search_elapsed_ms()} ms)",
            f"Binary Search time  : {self.binary_search_elapsed_ns} ns  "
            f"({self.binary_search_elapsed_ms()} ms)",
        ]

    def __repr__(self) -> str:
        return (
            f"AnalysisResult(n={self.student_count}, "
            f"avg={self.average_readiness:.1f}, "
            f"var={self.variance:.2f})"
        )
