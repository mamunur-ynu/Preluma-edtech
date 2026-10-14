"""Backward-compatibility shim — the topic library moved to ``core.topics``."""
from core.topics import (  # noqa: F401
    ALIASES,
    TOPIC_OPTIONS,
    TOPICS,
    canonical_key,
    concept,
    make_topic,
    validate_topics,
)
