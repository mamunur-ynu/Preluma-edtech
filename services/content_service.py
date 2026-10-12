"""
services/content_service.py — resolves a topic name to a validated topic pack.

Resolution order: curated library → live Wikipedia → generic fallback.  The caller always
receives the same structure, whichever source answered.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from core.content_pack import clean_text, ensure_pack_schema, make_generic_fallback
from core.topics import TOPICS, canonical_key

logger = logging.getLogger("preluma.content")

# Wikipedia is optional: if the dependency is unavailable we fall back to generic content.
try:
    from services.wiki_service import build_wiki_topic_pack
except Exception:  # pragma: no cover - defensive
    build_wiki_topic_pack = None


def build_pack(topic: str, use_wikipedia: bool = True) -> Dict:
    """
    Return a fully validated content pack for the requested topic.

    Resolution order:
      1. Curated local library (topics.py) — fastest, highest quality.
      2. Live Wikipedia data via wiki_fetcher — covers any topic.
      3. Generic fallback — always succeeds, content is minimal.

    The caller receives a consistent structure regardless of which source
    was used, so downstream functions require no source-specific logic.
    """
    requested = clean_text(topic) or "Machine Learning"
    key  = canonical_key(requested)
    data = TOPICS.get(key)

    if data:
        return ensure_pack_schema(data, data.get("title", requested.title()))

    if use_wikipedia and build_wiki_topic_pack is not None:
        try:
            wiki_pack = build_wiki_topic_pack(requested)
            if wiki_pack:
                return ensure_pack_schema(wiki_pack, wiki_pack.get("title", requested.title()))
        except Exception:
            logger.info("Wikipedia lookup failed for %r; using fallback", requested)

    return ensure_pack_schema(make_generic_fallback(requested.title()), requested.title())


def build_enriched_class_questions(pack: dict) -> List[str]:
    """Smart questions to ask in class: LLM-generated when a provider is available, curated otherwise."""
    try:
        from services import ai_service

        if ai_service.llm_available():
            result = ai_service.generate_class_questions(
                pack["title"], pack["definition"], list(pack.get("concepts", {}).keys())
            )
            if result:
                return result
    except Exception as exc:  # LLM problems must never break the mission flow
        logger.info("Falling back to curated class questions: %s", exc)
    return pack.get("class_questions", [])[:5]
