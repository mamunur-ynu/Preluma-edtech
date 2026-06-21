from __future__ import annotations
from typing import Any

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
