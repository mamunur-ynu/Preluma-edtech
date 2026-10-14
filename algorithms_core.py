"""Backward-compatibility shim — the implementation moved to ``core.algorithms``."""
from core.algorithms import (  # noqa: F401
    _key_value,
    _merge,
    add_normalized_name,
    binary_search_leftmost,
    collect_binary_search_matches,
    linear_search_by_name,
    merge_sort_records,
    normalize_name,
    timed_call,
)
