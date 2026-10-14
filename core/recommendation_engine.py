"""
core/recommendation_engine.py — builds a personal learning path.

Rule-based and fully explainable on purpose: every step carries the *reason* it was chosen, so
a student (or a teacher, or an examiner) can see why the platform suggests it.  An LLM can
later *rephrase* the steps (see ``services.recommendation_service``) but never decides them.

Example (from the product vision)::

    Python 85 %, Algorithms 45 %
    1. Revise  recursion                  ← weakest concept of the weak topic
    2. Practise searching algorithms      ← follow-up practice on the same topic
    3. Start   data structures            ← newly unlocked: its prerequisites are mastered

Ordering: ``revise`` → ``practice`` → ``advance`` → ``review``; inside a kind, the biggest gap
(or the most topics unlocked) comes first.  At least one ``advance`` step is kept when anything
is unlocked, so a student with weak spots still sees forward progress.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.knowledge_graph import Graph, dependants
from core.learning_engine import (
    STRONG_THRESHOLD,
    WEAK_THRESHOLD,
    MasteryKey,
    MasteryState,
    decayed_mastery,
    weakest_skill,
)
from typing import Mapping

KIND_ORDER = {"revise": 0, "practice": 1, "advance": 2, "review": 3}
MINUTES = {"revise": 15, "practice": 10, "advance": 20, "review": 8}
UNLOCK_THRESHOLD = 70.0          # prerequisites must be at least this strong to start a topic
REVIEW_BELOW = 65.0              # strong topic that has faded below this → quick review


@dataclass(frozen=True)
class PathStep:
    """One item of a learning path."""

    kind: str                    # revise | practice | advance | review
    topic: str                   # canonical topic key
    concept: str
    title: str
    reason: str
    score: float                 # larger = more urgent (within its kind)
    estimated_minutes: int = 10

    @property
    def priority_label(self) -> str:
        return {"revise": "Fix now", "practice": "Build up", "advance": "Next up", "review": "Refresh"}[self.kind]


def _title(graph: Graph, topic: str) -> str:
    node = graph.get(topic)
    return node.title if node else topic.title()


def _topic_states(profile: Mapping[MasteryKey, MasteryState]) -> dict[str, MasteryState]:
    return {t: s for (t, c), s in profile.items() if c == "" and t != "_skills" and s.attempts > 0}


def build_learning_path(
    profile: Mapping[MasteryKey, MasteryState],
    graph: Graph,
    *,
    now: datetime | None = None,
    max_steps: int = 5,
    focus_topics: set[str] | None = None,
) -> list[PathStep]:
    """Return up to ``max_steps`` ordered :class:`PathStep` items for one student.

    ``focus_topics`` (for example the topics of the student's enrolled courses) restricts
    *new-topic* suggestions; weaknesses are always addressed wherever they are.
    """
    now = now or datetime.utcnow()
    states = _topic_states(profile)
    skill = weakest_skill(profile)
    steps: list[PathStep] = []

    # 1 + 2 ─ weak topics: revise the weakest concept, then practise the topic
    for topic, state in states.items():
        if state.mastery >= WEAK_THRESHOLD:
            continue
        unlocks = len(dependants(graph, topic))
        concept_rows = sorted(
            ((c, s.mastery) for (t, c), s in profile.items() if t == topic and c and s.attempts > 0 and s.mastery < WEAK_THRESHOLD),
            key=lambda item: item[1],
        )
        gap = WEAK_THRESHOLD - state.mastery + 40 + unlocks * 2
        name = _title(graph, topic)
        if concept_rows:
            concept, c_mastery = concept_rows[0]
            steps.append(PathStep(
                "revise", topic, concept, f"Revise {concept} ({name})",
                f"Your score on “{concept}” is {c_mastery:.0f}% and {name} overall is {state.mastery:.0f}% — below the {WEAK_THRESHOLD:.0f}% line.",
                gap, MINUTES["revise"],
            ))
            second = concept_rows[1][0] if len(concept_rows) > 1 else ""
        else:
            steps.append(PathStep(
                "revise", topic, "", f"Revise the fundamentals of {name}",
                f"Your {name} score is {state.mastery:.0f}% — below the {WEAK_THRESHOLD:.0f}% line.",
                gap, MINUTES["revise"],
            ))
            second = ""
        focus = second or (f"{skill[0]} questions" if skill and skill[1] < STRONG_THRESHOLD else "mixed questions")
        steps.append(PathStep(
            "practice", topic, second, f"Practise {name} — focus on {focus}",
            f"Practice after revising locks the idea in; {focus} are where you lose the most marks.",
            gap - 5, MINUTES["practice"],
        ))

    # 2b ─ developing topics: more practice
    for topic, state in states.items():
        if WEAK_THRESHOLD <= state.mastery < STRONG_THRESHOLD:
            name = _title(graph, topic)
            steps.append(PathStep(
                "practice", topic, "", f"Practise {name}",
                f"{name} is at {state.mastery:.0f}% — a few more attempts will take you past {STRONG_THRESHOLD:.0f}%.",
                STRONG_THRESHOLD - state.mastery, MINUTES["practice"],
            ))

    # 3 ─ advance: start topics whose prerequisites are mastered
    for key, node in graph.items():
        if key in states:
            continue
        if focus_topics is not None and key not in focus_topics:
            continue
        prereq_states = [states.get(p) for p in node.prerequisites]
        if any(s is None or s.mastery < UNLOCK_THRESHOLD for s in prereq_states):
            continue
        strong = [s.mastery for s in prereq_states if s is not None]
        if node.prerequisites:
            reason = (
                "You have mastered the prerequisites: "
                + ", ".join(f"{_title(graph, p)} ({states[p].mastery:.0f}%)" for p in node.prerequisites)
                + "."
            )
            score = 40 + sum(strong) / len(strong) / 10 + len(dependants(graph, key))
        else:
            reason = "A good starting point — it has no prerequisites."
            score = 20 + len(dependants(graph, key))
        steps.append(PathStep("advance", key, "", f"Start {node.title}", reason, score, MINUTES["advance"]))

    # 4 ─ review: strong topics that have faded
    for topic, state in states.items():
        if state.mastery >= STRONG_THRESHOLD:
            faded = decayed_mastery(state, now)
            if faded < REVIEW_BELOW:
                name = _title(graph, topic)
                steps.append(PathStep(
                    "review", topic, "", f"Quick review of {name}",
                    f"You were at {state.mastery:.0f}% but haven't practised recently (about {faded:.0f}% now).",
                    REVIEW_BELOW - faded, MINUTES["review"],
                ))

    return _select(steps, max_steps)


def _select(steps: list[PathStep], max_steps: int) -> list[PathStep]:
    """Order, de-duplicate and trim, always keeping one ``advance`` step if available."""
    seen: set[tuple[str, str, str]] = set()
    unique = []
    for step in sorted(steps, key=lambda s: (KIND_ORDER[s.kind], -s.score, s.topic)):
        ident = (step.kind, step.topic, step.concept)
        if ident not in seen:
            seen.add(ident)
            unique.append(step)

    advance = [s for s in unique if s.kind == "advance"]
    others = [s for s in unique if s.kind != "advance"]
    if advance and others and max_steps >= 3:
        chosen = others[: max_steps - 1] + advance[:1]
    else:
        chosen = (others + advance)[:max_steps]
    return sorted(chosen, key=lambda s: (KIND_ORDER[s.kind], -s.score, s.topic))
