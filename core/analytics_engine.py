"""
core/analytics_engine.py — class-level analytics (pure Python, standard library only).

Contains the course-assessment statistics (mean, population variance, frequency tables — written
by hand on purpose, no numpy/pandas) plus the teacher-facing helpers built on top of the
hand-written sorting/searching in ``core.algorithms``.  Nothing here performs I/O; services
decide what to log or persist.
"""

from __future__ import annotations

from typing import Any, Iterable

from core.algorithms import (
    add_normalized_name,
    collect_binary_search_matches,
    linear_search_by_name,
    merge_sort_records,
    timed_call,
)

def extract_numeric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        try:
            values.append(float(row.get(field, 0.0)))
        except (TypeError, ValueError):
            continue
    return values

def mean(values: list[float]) -> float:
    total = 0.0
    count = 0
    for value in values:
        total += float(value)
        count += 1
    return total / count if count else 0.0

def population_variance(values: list[float]) -> float:
    count = 0
    for _ in values:
        count += 1
    if count == 0:
        return 0.0
    avg = mean(values)
    total = 0.0
    for value in values:
        d = float(value) - avg
        total += d * d
    return total / count

def frequency_table(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field, "Unknown") or "Unknown")
        counts[key] = counts.get(key, 0) + 1
    return [{"Weak Skill": key, "Count": count} for key, count in counts.items()]

def readiness_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    values = extract_numeric_values(rows, "Readiness")
    weak = set()
    for row in rows:
        weak.add(str(row.get("Weak Skill", "")))
    return {
        "students_tracked": len(rows),
        "class_average": round(mean(values), 1),
        "population_variance": round(population_variance(values), 2),
        "unique_weak_skills": len(weak),
    }


# ---------------------------------------------------------------------------
# Teacher-facing helpers (moved from teacher.py; now free of storage side effects)
# ---------------------------------------------------------------------------

def readiness_label(score: float) -> str:
    """Human label for a readiness percentage."""
    if score >= 85:
        return "Lecture Ready"
    if score >= 70:
        return "Almost Ready"
    if score >= 50:
        return "Needs Review"
    return "At Risk"


def class_average_readiness(rows: list[dict[str, Any]]) -> float:
    return float(readiness_summary(rows)["class_average"])


def analyze_class(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summary + both sort orders (with nanosecond timings) for the Teacher Studio tables."""
    summary = readiness_summary(rows)
    sorted_by_readiness, sort_ns = timed_call(merge_sort_records, rows, "Readiness", True)
    rows_named = add_normalized_name(rows)
    sorted_by_name, name_sort_ns = timed_call(merge_sort_records, rows_named, "student_name_norm", False)
    return {
        "summary": summary,
        "weak_skill_frequency": frequency_table(rows, "Weak Skill"),
        "sorted_by_readiness": sorted_by_readiness,
        "sorted_by_name": sorted_by_name,
        "sort_readiness_ns": sort_ns,
        "sort_name_ns": name_sort_ns,
    }


def search_by_name(rows: list[dict[str, Any]], target_name: str) -> dict[str, Any]:
    """Linear search vs. sort + binary search, both timed (course requirement)."""
    rows_named = add_normalized_name(rows)
    linear, linear_ns = timed_call(linear_search_by_name, rows_named, target_name)
    sorted_by_name, sort_ns = timed_call(merge_sort_records, rows_named, "student_name_norm", False)
    binary, binary_ns = timed_call(collect_binary_search_matches, sorted_by_name, target_name)
    return {
        "linear_result": linear,
        "binary_result": binary,
        "linear_ns": linear_ns,
        "binary_ns": binary_ns,
        "sort_ns": sort_ns,
        "total_binary_pipeline_ns": sort_ns + binary_ns,
    }


# ---------------------------------------------------------------------------
# Dashboard analytics (new)
# ---------------------------------------------------------------------------

READINESS_BANDS = (
    ("At Risk", 0.0, 50.0),
    ("Needs Review", 50.0, 70.0),
    ("Almost Ready", 70.0, 85.0),
    ("Lecture Ready", 85.0, 100.0001),
)


def score_distribution(scores: Iterable[float]) -> list[dict[str, Any]]:
    """Count scores per readiness band (for the class histogram)."""
    counts = {label: 0 for label, _, _ in READINESS_BANDS}
    for value in scores:
        for label, low, high in READINESS_BANDS:
            if low <= float(value) < high:
                counts[label] += 1
                break
    return [{"band": label, "count": counts[label]} for label, _, _ in READINESS_BANDS]


def completion_rate(completed: int, total: int) -> float:
    """Percentage (0–100, one decimal) of ``completed`` out of ``total``."""
    return round(100.0 * completed / total, 1) if total > 0 else 0.0


def topic_difficulty_ranking(
    mastery_rows: Iterable[dict[str, Any]], at_risk_below: float = 60.0
) -> list[dict[str, Any]]:
    """Rank topics from hardest to easiest for this class.

    ``mastery_rows`` items need ``topic`` and ``mastery`` (0–100).  Returns, per topic,
    the average mastery, how many students were measured and how many are below the line.
    """
    buckets: dict[str, list[float]] = {}
    for row in mastery_rows:
        buckets.setdefault(str(row.get("topic", "")), []).append(float(row.get("mastery", 0.0)))
    ranking = [
        {
            "topic": topic,
            "average_mastery": round(mean(values), 1),
            "students": len(values),
            "students_at_risk": sum(1 for v in values if v < at_risk_below),
        }
        for topic, values in buckets.items()
        if topic
    ]
    ranking.sort(key=lambda item: item["average_mastery"])
    return ranking
