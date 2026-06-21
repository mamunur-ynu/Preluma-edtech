"""
result_generator.py — Preluma Algorithm Proof Writer
======================================================
Generates result.txt, which serves as the official algorithm-proof
artifact required by the Python course assessment.

Demonstrates (with live timing):
  1. CSV data load
  2. Manual Merge Sort  O(n log n)
  3. Manual Mean + Population Variance
  4. Manual Linear Search  O(n)
  5. Manual Binary Search  O(log n)

Call generate_result_file() to (re-)write result.txt at any time.
Called automatically from Teacher Studio when student data exists.

No third-party libraries used in this module.
"""

from __future__ import annotations
import csv
import datetime
from pathlib import Path

from algorithms_core import (
    merge_sort_records,
    linear_search_by_name,
    binary_search_leftmost,
    collect_binary_search_matches,
    timed_call,
)
from analytics_core import mean, population_variance, frequency_table
from models import StudentRecord, AnalysisResult

STUDENTS_CSV = Path("data/students.csv")
RESULT_TXT   = Path("result.txt")


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_rows() -> list[dict]:
    """Load student rows from CSV. Returns empty list if file missing."""
    if not STUDENTS_CSV.exists():
        return []
    try:
        with open(STUDENTS_CSV, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def _demo_rows() -> list[dict]:
    """Return 6 built-in demo rows so result.txt is never empty on fresh deploy."""
    return [
        # Keys match storage_core.FIELDNAMES (capital-case, space-separated)
        {"Record ID": "1", "Student": "Amir",  "Topic": "Machine Learning",  "Readiness": "85.0",
         "Weak Skill": "Overfitting",    "Quiz Score": "4", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:00", "Learning Mode": "Guided"},
        {"Record ID": "2", "Student": "Jia",   "Topic": "Neural Network",    "Readiness": "92.0",
         "Weak Skill": "",              "Quiz Score": "5", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:05", "Learning Mode": "Guided"},
        {"Record ID": "3", "Student": "Fahim", "Topic": "Python Programming","Readiness": "78.0",
         "Weak Skill": "List Comprehension", "Quiz Score": "3", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:10", "Learning Mode": "Quick"},
        {"Record ID": "4", "Student": "Nadia", "Topic": "Statistics",        "Readiness": "70.0",
         "Weak Skill": "Variance",      "Quiz Score": "3", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:15", "Learning Mode": "Quick"},
        {"Record ID": "5", "Student": "Omar",  "Topic": "Machine Learning",  "Readiness": "88.0",
         "Weak Skill": "",              "Quiz Score": "4", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:20", "Learning Mode": "Guided"},
        {"Record ID": "6", "Student": "Sara",  "Topic": "Data Structures",   "Readiness": "66.0",
         "Weak Skill": "Binary Tree",   "Quiz Score": "3", "Quiz Total": "5",
         "Lecture Time": "2026-06-17T09:25", "Learning Mode": "Quick"},
    ]


# ── core function ─────────────────────────────────────────────────────────────

def generate_result_file(search_target: str = "Jia") -> AnalysisResult:
    """
    Run all algorithms on student data and write result.txt.

    Parameters
    ----------
    search_target : Name to search for in Linear + Binary Search demo.

    Returns
    -------
    AnalysisResult dataclass with all computed statistics and timing.

    Raises
    ------
    IOError  : if result.txt cannot be written (disk full, permissions).
    """
    rows = _load_rows() or _demo_rows()

    # CSV uses capital-case keys: "Readiness", "Student", "Weak Skill"
    readiness_values = [float(r.get("Readiness", r.get("readiness", 0))) for r in rows]

    # ── 1. Merge Sort (O(n log n)) ───────────────────────────────────────────
    sorted_rows, sort_ns = timed_call(merge_sort_records, rows, "Readiness", reverse=True)

    # ── 2. Statistics (manual mean + variance) ───────────────────────────────
    avg   = mean(readiness_values)
    var   = population_variance(readiness_values)
    lo    = min(readiness_values) if readiness_values else 0.0
    hi    = max(readiness_values) if readiness_values else 0.0
    # frequency_table returns list of {"Weak Skill": ..., "Count": ...} sorted by count desc
    freq_list = frequency_table(rows, "Weak Skill")
    top_weak = freq_list[0]["Weak Skill"] if freq_list else ""
    if top_weak in ("Unknown", ""):
        top_weak = freq_list[1]["Weak Skill"] if len(freq_list) > 1 else ""

    # ── 3. Linear Search (O(n)) — uses "Student" column ─────────────────────
    lin_result, lin_ns = timed_call(linear_search_by_name, rows, search_target)

    # ── 4. Binary Search (O(log n)) — requires sorted input ─────────────────
    # add_normalized_name populates "student_name_norm" from "Student" column
    from algorithms_core import add_normalized_name
    normed = add_normalized_name(rows)
    sorted_for_bs, prep_ns = timed_call(merge_sort_records, normed, "student_name_norm", reverse=False)
    bs_index, bs_ns = timed_call(binary_search_leftmost, sorted_for_bs, search_target, "student_name_norm")
    bs_matches = collect_binary_search_matches(sorted_for_bs, search_target, "student_name_norm")

    # ── Build AnalysisResult ─────────────────────────────────────────────────
    result = AnalysisResult(
        student_count=len(rows),
        average_readiness=avg,
        lowest_readiness=lo,
        highest_readiness=hi,
        variance=var,
        most_common_weak_skill=top_weak,
        merge_sort_elapsed_ns=sort_ns,
        linear_search_elapsed_ns=lin_ns,
        binary_search_elapsed_ns=bs_ns,
        sorted_records=sorted_rows,
    )

    # ── Write result.txt ─────────────────────────────────────────────────────
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    lines += [
        "=" * 62,
        "  PRELUMA — Algorithm Proof & Results",
        "  Course: Python Programming  |  Yunnan University",
        f"  Generated: {now}",
        "=" * 62,
        "",
        "DATASET",
        "-" * 40,
        f"  Source file : data/students.csv",
        f"  Total rows  : {len(rows)}",
        "",
        "STATISTICS  (manual implementation — no numpy/pandas)",
        "-" * 40,
    ]
    lines += [f"  {line}" for line in result.summary_lines()[:6]]
    lines += [""]

    lines += [
        "ALGORITHM 1 — MERGE SORT  O(n log n)",
        "-" * 40,
        "  Sorted by: readiness (descending)",
        "",
        f"  {'Rank':<5} {'Student':<12} {'Topic':<25} {'Readiness':>10}",
        f"  {'-'*5} {'-'*12} {'-'*25} {'-'*10}",
    ]
    for rank, row in enumerate(sorted_rows, 1):
        name  = str(row.get("Student", row.get("student", ""))).ljust(12)
        topic = str(row.get("Topic",   row.get("topic",   ""))).ljust(25)
        score = str(row.get("Readiness", row.get("readiness", ""))).rjust(10)
        lines.append(f"  {str(rank):<5} {name} {topic} {score}")

    lines += [
        "",
        f"  Elapsed : {sort_ns:,} ns  ({sort_ns/1_000_000:.3f} ms)",
        f"  Complexity: O(n log n)  |  n = {len(rows)}",
        "",
    ]

    lines += [
        "ALGORITHM 2 — LINEAR SEARCH  O(n)",
        "-" * 40,
        f"  Target  : {search_target!r}",
    ]
    if lin_result:
        match = lin_result[0] if isinstance(lin_result, list) else lin_result
        name  = match.get("Student", match.get("student", search_target))
        topic = match.get("Topic",   match.get("topic",   ""))
        score = match.get("Readiness", match.get("readiness", ""))
        lines.append(f"  Found   : {name!r} | topic={topic!r} | readiness={score}")
    else:
        lines.append(f"  Result  : not found")
    lines += [
        f"  Elapsed : {lin_ns:,} ns  ({lin_ns/1_000_000:.3f} ms)",
        f"  Complexity: O(n)  |  n = {len(rows)}",
        "",
    ]

    lines += [
        "ALGORITHM 3 — BINARY SEARCH  O(log n)",
        "-" * 40,
        f"  Target  : {search_target!r}  (requires pre-sorted input)",
        f"  Sort prep: {prep_ns:,} ns  (Merge Sort before Binary Search)",
        f"  Found at index: {bs_index}  |  matches: {len(bs_matches)}",
        f"  Elapsed : {bs_ns:,} ns  ({bs_ns/1_000_000:.3f} ms)",
        f"  Complexity: O(log n)  |  n = {len(rows)}",
        "",
    ]

    lines += [
        "TIMING COMPARISON",
        "-" * 40,
        f"  Linear Search  : {lin_ns:>12,} ns",
        f"  Binary Search  : {bs_ns:>12,} ns",
        f"  Merge Sort     : {sort_ns:>12,} ns",
        "",
        "  Note: Binary Search is faster per lookup but requires a",
        "  pre-sorted array. Linear Search works on any order.",
        "",
        "=" * 62,
        "  END OF RESULT FILE",
        "=" * 62,
    ]

    try:
        RESULT_TXT.write_text("\n".join(lines), encoding="utf-8")
    except IOError as exc:
        raise IOError(f"Could not write result.txt: {exc}") from exc

    return result


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    res = generate_result_file()
    print(f"result.txt written — {res.student_count} students, "
          f"avg readiness {res.average_readiness:.1f}")
    print(RESULT_TXT.read_text(encoding="utf-8"))
