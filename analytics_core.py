"""Backward-compatibility shim — the implementation moved to ``core.analytics_engine``."""
from core.analytics_engine import (  # noqa: F401
    extract_numeric_values,
    frequency_table,
    mean,
    population_variance,
    readiness_summary,
)
