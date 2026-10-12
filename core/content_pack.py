"""
core/content_pack.py — the shape of a *topic pack* and pure helpers around it.

A topic pack is a plain ``dict`` (title, hook, definition, simple, facts, concepts,
applications, misconceptions, class_questions).  Packs come from three places — the curated
library (``core.topics``), Wikipedia (``services.wiki_service``) or a generic fallback — and
:func:`ensure_pack_schema` guarantees that every pack has every key the rest of the app needs.

Pure Python, standard library only (course constraint).  Moved here unchanged from ``engine.py``.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple


# Default structure applied when a concept entry is missing certain fields.
# This prevents KeyError exceptions in downstream rendering logic.
DEFAULT_CONCEPT = {
    "definition": "This is the main idea of the topic.",
    "kid":        "Start with the simplest meaning first, then add examples.",
    "example":    "Connect the idea to a real-life situation.",
    "mistake":    "Do not memorize words without understanding the meaning.",
    "exam":       "In class, explain definition, example, and common mistake.",
}


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalise whitespace in a string and strip leading/trailing spaces."""
    return re.sub(r"\s+", " ", str(text).strip())


# ---------------------------------------------------------------------------
# Fallback content builder
# ---------------------------------------------------------------------------

def make_generic_fallback(title: str) -> Dict:
    """
    Build a minimal but complete content pack for topics that are not
    in the local library and cannot be retrieved from Wikipedia.

    The fallback keeps the app functional for any topic a student enters,
    while making it clear through neutral language that content is limited.
    """
    return {
        "title": title,
        "hook": f"{title} becomes easier when we break it into small ideas.",
        "definition": (
            f"{title} is an academic topic that can be understood through "
            "definition, examples, applications, and common mistakes."
        ),
        "simple": f"Think of {title} like building blocks: first one block, then another.",
        "facts": [
            f"{title} has a main definition.",
            f"{title} becomes clearer through examples.",
            f"{title} can be discussed in class using smart questions.",
        ],
        "concepts": {
            "main idea": {
                "definition": f"The main idea of {title} is the first meaning a student should understand.",
                "kid":        f"{title} is easier when we explain it in tiny steps.",
                "example":    "A new topic is like a map: first see the big roads, then learn the details.",
                "mistake":    "Do not memorize without examples.",
                "exam":       "Give definition, simple example, and one common mistake.",
            }
        },
        "applications": {
            "class learning": "Helps students prepare before lectures."
        },
        "misconceptions": [
            f"{title} is not only memorization.",
            "A hard topic becomes easier when explained with examples.",
            "Good preparation means asking better questions in class.",
        ],
        "class_questions": [
            f"What is the simplest definition of {title}?",
            f"Where is {title} used in real life?",
            f"What is the most common mistake in {title}?",
            f"How can I explain {title} to a beginner?",
            f"What should I ask the teacher about {title}?",
        ],
    }


# ---------------------------------------------------------------------------
# Schema validation and normalisation
# ---------------------------------------------------------------------------

def ensure_pack_schema(data: Dict, requested_title: str) -> Dict:
    """
    Validate and normalise a raw content pack so every key the rest of the
    system expects is always present.

    Missing fields receive sensible defaults rather than raising exceptions.
    Every concept entry is also merged with DEFAULT_CONCEPT so partial data
    from Wikipedia does not break the question generator.
    """
    pack = dict(data or {})

    # Top-level fields with safe defaults
    pack.setdefault("title",  requested_title)
    pack.setdefault("hook",   f"{requested_title} becomes easier when the student sees the big picture first.")
    pack.setdefault("definition", f"{requested_title} is an academic topic.")
    pack.setdefault("simple", f"Think of {requested_title} as a map: first learn the main roads, then the details make sense.")
    pack.setdefault("facts",         [])
    pack.setdefault("concepts",      {})
    pack.setdefault("applications",  {})
    pack.setdefault("misconceptions",[])
    pack.setdefault("class_questions",[])

    # Guarantee at least one concept entry
    if not pack["concepts"]:
        pack["concepts"] = {"main idea": dict(DEFAULT_CONCEPT)}

    # Merge each concept with DEFAULT_CONCEPT so no field is ever missing
    fixed = {}
    for name, concept in pack["concepts"].items():
        item = dict(DEFAULT_CONCEPT)
        item.update(concept or {})
        fixed[name] = item
    pack["concepts"] = fixed

    # Populate list fields if they arrived empty
    if not pack["facts"]:
        pack["facts"] = [
            pack["definition"],
            pack["simple"],
            "Understanding the core idea improves class participation.",
        ]
    if not pack["misconceptions"]:
        pack["misconceptions"] = [f"{pack['title']} is not only memorization."]
    if not pack["class_questions"]:
        pack["class_questions"] = [
            f"What is {pack['title']}?",
            f"Where is {pack['title']} used?",
            "What is one common mistake?",
            "How can I explain it simply?",
            "What should I ask in class?",
        ]

    return pack


# ---------------------------------------------------------------------------
# Concept helpers
# ---------------------------------------------------------------------------

def _first_concept(pack: Dict) -> Tuple[str, Dict]:
    """Return the name and data of the first concept in the pack."""
    name = next(iter(pack["concepts"]))
    return name, pack["concepts"][name]


def best_concept_match(pack: Dict, question: str) -> Tuple[str, Dict]:
    """
    Find the concept whose name best matches the student's question text.

    The search works in two passes: an exact substring match, then a
    word-level match for concept names with multiple words. If nothing
    matches, the first concept is returned as a safe default.
    """
    q = clean_text(question).lower()

    for name, concept in pack["concepts"].items():
        if name.lower() in q:
            return name, concept

    for name, concept in pack["concepts"].items():
        for word in name.lower().split():
            if len(word) > 3 and word in q:
                return name, concept

    return _first_concept(pack)


# ---------------------------------------------------------------------------
# Brain Brief builder
# ---------------------------------------------------------------------------

def build_brain_brief(pack: Dict) -> Dict:
    """
    Extract the key learning points from a pack into a compact brief.

    The Brain Brief is shown to students at the start of each mission as a
    two-minute primer: one clear definition, a simple analogy, a real-life
    example, a misconception to avoid, and three verifiable facts.
    """
    name, c = _first_concept(pack)
    return {
        "title":          pack["title"],
        "tiny_answer":    pack["definition"],
        "simple":         pack["simple"],
        "hook":           pack["hook"],
        "key_concept":    name.title(),
        "concept_simple": c["kid"],
        "example":        c["example"],
        "misconception":  pack["misconceptions"][0],
        "facts":          pack["facts"][:3],
        "class_questions":pack["class_questions"][:5],
    }


# ---------------------------------------------------------------------------
# Tutor sections (offline answer from the pack)
# ---------------------------------------------------------------------------

def tutor_sections(pack: Dict, question: str, style: str = "Normal Mode") -> Dict:
    """
    Build a structured tutor response for a student's free-text question.

    The function finds the concept within the pack that best matches the
    question and returns a response object with a plain definition, a
    beginner-friendly explanation, a real-life example, the most common
    mistake, and an exam-focused angle.
    """
    name, c = best_concept_match(pack, question)
    return {
        "topic":            pack["title"],
        "concept":          name.title(),
        "tiny_answer":      c["definition"],
        "explain_simply":   c["kid"],
        "real_life_example":c["example"],
        "common_mistake":   c["mistake"],
        "exam_angle":       c["exam"],
        "memory_line":      f"Remember {name.title()} through this example: {c['example']}",
    }
