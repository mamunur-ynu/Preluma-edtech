from __future__ import annotations
from typing import Any
from algorithms_core import add_normalized_name, collect_binary_search_matches, linear_search_by_name, merge_sort_records, timed_call
from analytics_core import frequency_table, readiness_summary
from storage_core import append_result_log, load_student_rows, seed_demo_rows

def readiness_label(score: float) -> str:
    if score >= 85: return "Lecture Ready"
    if score >= 70: return "Almost Ready"
    if score >= 50: return "Needs Review"
    return "At Risk"

def get_teacher_rows(latest_session: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    seed_demo_rows()
    rows = load_student_rows()
    if latest_session:
        rows.append(dict(latest_session))
    return rows

def build_teacher_dataframe(latest_session: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return get_teacher_rows(latest_session)

def class_average_readiness(rows: list[dict[str, Any]]) -> float:
    return float(readiness_summary(rows)["class_average"])

def teacher_analytics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = readiness_summary(rows)
    sorted_by_readiness, sort_ns = timed_call(merge_sort_records, rows, "Readiness", True)
    rows_named = add_normalized_name(rows)
    sorted_by_name, name_sort_ns = timed_call(merge_sort_records, rows_named, "student_name_norm", False)
    append_result_log("merge_sort_readiness", {"n": len(rows), "elapsed_ns": sort_ns})
    append_result_log("merge_sort_name", {"n": len(rows), "elapsed_ns": name_sort_ns})
    return {
        "summary": summary,
        "weak_skill_frequency": frequency_table(rows, "Weak Skill"),
        "sorted_by_readiness": sorted_by_readiness,
        "sorted_by_name": sorted_by_name,
        "sort_readiness_ns": sort_ns,
        "sort_name_ns": name_sort_ns,
    }

def search_student(rows: list[dict[str, Any]], target_name: str) -> dict[str, Any]:
    rows_named = add_normalized_name(rows)
    linear, linear_ns = timed_call(linear_search_by_name, rows_named, target_name)
    sorted_by_name, sort_ns = timed_call(merge_sort_records, rows_named, "student_name_norm", False)
    binary, binary_ns = timed_call(collect_binary_search_matches, sorted_by_name, target_name)
    append_result_log("linear_search", {"target": target_name, "n": len(rows), "elapsed_ns": linear_ns, "matches": len(linear)})
    append_result_log("binary_search", {"target": target_name, "n": len(rows), "elapsed_ns": binary_ns, "matches": len(binary)})
    append_result_log("merge_sort_for_binary_search", {"n": len(rows), "elapsed_ns": sort_ns})
    return {"linear_result": linear, "binary_result": binary, "linear_ns": linear_ns, "binary_ns": binary_ns, "sort_ns": sort_ns, "total_binary_pipeline_ns": sort_ns + binary_ns}
