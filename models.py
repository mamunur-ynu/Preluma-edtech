"""Backward-compatibility shim — the record dataclasses moved to ``core.records``.

(The relational ORM models live in ``database.models``.)
"""
from core.records import AnalysisResult, StudentRecord  # noqa: F401
