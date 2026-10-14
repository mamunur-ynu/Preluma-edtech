"""
Backward-compatibility shim for the former ``engine.py``.

The code was split by responsibility (see docs/ARCHITECTURE.md):

* ``core.content_pack``      — topic-pack schema, brain brief, tutor sections
* ``core.assessment_engine`` — question generation and grading
* ``services.content_service`` — pack resolution (library → Wikipedia → fallback)
"""
from core.assessment_engine import (  # noqa: F401
    SKILL_APPLICATION,
    SKILL_CORE,
    SKILL_DEFINITION,
    SKILL_MISCONCEPTION,
    grade,
    make_questions,
)
from core.content_pack import (  # noqa: F401
    DEFAULT_CONCEPT,
    best_concept_match,
    build_brain_brief,
    clean_text,
    ensure_pack_schema,
    make_generic_fallback,
    tutor_sections,
)
from services.content_service import build_enriched_class_questions, build_pack  # noqa: F401
