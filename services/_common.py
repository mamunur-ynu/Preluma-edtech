"""Small helpers shared by the services."""

from __future__ import annotations

from datetime import datetime, timezone

from core.topics import canonical_key


def topic_key(topic: str) -> str:
    """Canonical lowercase key for any topic name, title or alias ("ML" → "machine learning")."""
    return canonical_key(str(topic or "").strip())


def now_utc() -> datetime:
    """Naive UTC "now" (matches ``database.models.utcnow``)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def title_for(key: str) -> str:
    """Display title of a topic key (curated title if known, else Title Case)."""
    from core.topics import TOPICS

    pack = TOPICS.get(key)
    return str(pack["title"]) if pack and pack.get("title") else key.title()
