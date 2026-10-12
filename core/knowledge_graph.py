"""
core/knowledge_graph.py — which topics build on which.

The recommendation engine needs to know that *Neural Networks* should wait until *Machine
Learning* is solid.  The relationships below are a deliberate, human-reviewed curriculum map
for the 28 curated topic packs in ``core.topics`` (keys are the canonical lowercase topic keys).

``build_graph()`` merges this map with the concept names found in the topic packs, so a
recommendation can say *"Revise overfitting"* instead of just *"Revise Machine Learning"*.
Topics that are not in the map (for example a custom Wikipedia topic) are treated as
stand-alone: no prerequisites, never suggested as a "next topic".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from core.topics import TOPICS

# topic key -> prerequisite topic keys
PREREQUISITES: dict[str, tuple[str, ...]] = {
    "python programming": (),
    "statistics": (),
    "artificial intelligence": (),
    "database management system": (),
    "computer network": (),
    "operating system": (),
    "quantum mechanics": (),
    "urban water management": (),
    "data structures": ("python programming",),
    "algorithms and complexity": ("python programming",),
    "software engineering": ("python programming",),
    "machine learning": ("python programming", "statistics"),
    "linear regression": ("statistics",),
    "logistic regression": ("linear regression",),
    "decision tree": ("machine learning", "data structures"),
    "neural network": ("machine learning",),
    "convolutional neural network": ("neural network",),
    "computer vision": ("convolutional neural network",),
    "natural language processing": ("neural network",),
    "reinforcement learning": ("machine learning",),
    "big data": ("database management system",),
    "api development": ("software engineering", "computer network"),
    "devops": ("software engineering",),
    "cloud computing": ("computer network", "operating system"),
    "cybersecurity": ("computer network",),
    "blockchain": ("data structures", "cybersecurity"),
    "internet of things": ("computer network",),
    "quantum computing": ("quantum mechanics",),
}


@dataclass(frozen=True)
class TopicNode:
    """One topic in the curriculum graph."""

    key: str
    title: str
    prerequisites: tuple[str, ...]
    concepts: tuple[str, ...]


Graph = Mapping[str, TopicNode]


def build_graph(topics: Mapping[str, dict] | None = None) -> dict[str, TopicNode]:
    """Create the graph from topic packs (defaults to the curated library)."""
    source = TOPICS if topics is None else topics
    graph: dict[str, TopicNode] = {}
    for key, pack in source.items():
        prereqs = tuple(p for p in PREREQUISITES.get(key, ()) if p in source)
        graph[key] = TopicNode(
            key=key,
            title=str(pack.get("title", key.title())),
            prerequisites=prereqs,
            concepts=tuple(pack.get("concepts", {}).keys()),
        )
    return graph


def dependants(graph: Graph, key: str) -> list[str]:
    """Topics that list ``key`` as a prerequisite (how many things it unlocks)."""
    return [node.key for node in graph.values() if key in node.prerequisites]


def has_cycle(graph: Graph) -> bool:
    """Sanity check used by the tests: a curriculum graph must be acyclic."""
    state: dict[str, int] = {}

    def visit(key: str) -> bool:
        if state.get(key) == 1:
            return True
        if state.get(key) == 2:
            return False
        state[key] = 1
        for parent in graph[key].prerequisites if key in graph else ():
            if visit(parent):
                return True
        state[key] = 2
        return False

    return any(visit(key) for key in graph)
