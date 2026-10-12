"""
Backward-compatibility shim for the former ``teacher.py`` (Teacher Studio helpers).

The pure arithmetic moved to ``core.analytics_engine``.  The functions here keep their old
behaviour *including* the audit-log side effect (one ``result.txt`` line per operation), which
is persistence and therefore stays outside ``core``.
"""
from __future__ import annotations

from typing import Any

from core.analytics_engine import analyze_class, class_average_readiness, readiness_label, search_by_name  # noqa: F401
from storage_core import append_result_log, load_student_rows, seed_demo_rows


def get_teacher_rows(latest_session: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    seed_demo_rows()
    rows = load_student_rows()
    if latest_session:
        rows.append(dict(latest_session))
    return rows


def build_teacher_dataframe(latest_session: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Kept for compatibility: returns a list of dict rows (not a DataFrame)."""
    return get_teacher_rows(latest_session)


def teacher_analytics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = analyze_class(rows)
    append_result_log("merge_sort_readiness", {"n": len(rows), "elapsed_ns": result["sort_readiness_ns"]})
    append_result_log("merge_sort_name", {"n": len(rows), "elapsed_ns": result["sort_name_ns"]})
    return result


def search_student(rows: list[dict[str, Any]], target_name: str) -> dict[str, Any]:
    result = search_by_name(rows, target_name)
    n = len(rows)
    append_result_log("linear_search", {"target": target_name, "n": n, "elapsed_ns": result["linear_ns"], "matches": len(result["linear_result"])})
    append_result_log("binary_search", {"target": target_name, "n": n, "elapsed_ns": result["binary_ns"], "matches": len(result["binary_result"])})
    append_result_log("merge_sort_for_binary_search", {"n": n, "elapsed_ns": result["sort_ns"]})
    return result
