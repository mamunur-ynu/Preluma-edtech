from __future__ import annotations
from time import perf_counter_ns
from typing import Any, Callable

def normalize_name(name: str) -> str:
    return " ".join(str(name).strip().casefold().split())

def timed_call(function: Callable, *args, **kwargs) -> tuple[Any, int]:
    start = perf_counter_ns()
    result = function(*args, **kwargs)
    return result, perf_counter_ns() - start

def _key_value(row: dict[str, Any], key: str) -> Any:
    value = row.get(key, "")
    if key == "Readiness":
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    return str(value)

def merge_sort_records(rows: list[dict[str, Any]], key: str, reverse: bool = False) -> list[dict[str, Any]]:
    if len(rows) <= 1:
        return rows[:]
    mid = len(rows) // 2
    left = merge_sort_records(rows[:mid], key, reverse)
    right = merge_sort_records(rows[mid:], key, reverse)
    return _merge(left, right, key, reverse)

def _merge(left: list[dict[str, Any]], right: list[dict[str, Any]], key: str, reverse: bool) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    i = j = 0
    while i < len(left) and j < len(right):
        lv = _key_value(left[i], key)
        rv = _key_value(right[j], key)
        take_left = lv >= rv if reverse else lv <= rv
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    while i < len(left):
        merged.append(left[i])
        i += 1
    while j < len(right):
        merged.append(right[j])
        j += 1
    return merged

def add_normalized_name(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        new = dict(row)
        new["student_name_norm"] = normalize_name(row.get("Student", ""))
        output.append(new)
    return output

def linear_search_by_name(rows: list[dict[str, Any]], target_name: str) -> list[dict[str, Any]]:
    target = normalize_name(target_name)
    found = []
    for row in rows:
        name = row.get("student_name_norm") or normalize_name(row.get("Student", ""))
        if name == target:
            found.append(row)
    return found

def binary_search_leftmost(rows: list[dict[str, Any]], target_name: str, key: str = "student_name_norm") -> int:
    target = normalize_name(target_name)
    low, high, answer = 0, len(rows) - 1, -1
    while low <= high:
        mid = low + (high - low) // 2
        value = str(rows[mid].get(key, ""))
        if value == target:
            answer = mid
            high = mid - 1
        elif value < target:
            low = mid + 1
        else:
            high = mid - 1
    return answer

def collect_binary_search_matches(rows: list[dict[str, Any]], target_name: str, key: str = "student_name_norm") -> list[dict[str, Any]]:
    index = binary_search_leftmost(rows, target_name, key)
    if index == -1:
        return []
    target = normalize_name(target_name)
    out = []
    while index < len(rows) and str(rows[index].get(key, "")) == target:
        out.append(rows[index])
        index += 1
    return out
