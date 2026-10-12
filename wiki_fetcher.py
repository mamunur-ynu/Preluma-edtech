"""Backward-compatibility shim — Wikipedia retrieval moved to ``services.wiki_service``."""
from services.wiki_service import *  # noqa: F401,F403
from services.wiki_service import (  # noqa: F401
    WikiResult,
    build_wiki_topic_pack,
    extract_keywords,
    fetch_wikipedia,
    search_wikipedia,
    simplify_text,
    smart_answer_from_pack,
)
