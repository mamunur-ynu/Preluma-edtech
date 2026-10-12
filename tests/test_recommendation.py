"""Rule-based, explainable recommendations (the spec example included)."""

from datetime import datetime, timedelta

from auth import create_user
from core.knowledge_graph import build_graph
from core.learning_engine import MasteryState
from core.recommendation_engine import build_learning_path
from services import learning_service, recommendation_service

NOW = datetime(2026, 1, 10, 12, 0)


def _profile(**topics):
    return {(name.replace("_", " "), ""): MasteryState(mastery=m, attempts=2, last_practiced_at=NOW) for name, m in topics.items()}


def test_spec_example_python_strong_algorithms_weak():
    """Python 85 %, Algorithms weak  →  Revise → Practise → Start next topic."""
    profile = _profile(python_programming=85, algorithms_and_complexity=40)
    steps = build_learning_path(profile, build_graph(), now=NOW, max_steps=3)
    assert [s.kind for s in steps] == ["revise", "practice", "advance"]
    assert steps[0].topic == "algorithms and complexity"
    assert "40%" in steps[0].reason                              # the reason is explainable
    assert steps[2].topic != "python programming"


def test_new_topics_unlock_only_when_prerequisites_are_strong():
    steps = build_learning_path(_profile(python_programming=50), build_graph(), now=NOW, max_steps=10)
    assert "data structures" not in {s.topic for s in steps if s.kind == "advance"}
    steps = build_learning_path(_profile(python_programming=90), build_graph(), now=NOW, max_steps=10)
    assert "data structures" in {s.topic for s in steps if s.kind == "advance"}


def test_faded_strong_topics_get_a_review_step():
    old = {("statistics", ""): MasteryState(mastery=92, attempts=4, last_practiced_at=NOW - timedelta(days=150))}
    kinds = {s.kind for s in build_learning_path(old, build_graph(), now=NOW, max_steps=10)}
    assert "review" in kinds


def test_empty_profile_suggests_starting_points():
    steps = build_learning_path({}, build_graph(), now=NOW, max_steps=3)
    assert steps and all(s.kind == "advance" for s in steps)


def test_max_steps_is_respected_and_deterministic():
    profile = _profile(python_programming=40, statistics=45, machine_learning=30)
    first = build_learning_path(profile, build_graph(), now=NOW, max_steps=4)
    assert len(first) == 4 and first == build_learning_path(profile, build_graph(), now=NOW, max_steps=4)


def test_service_stores_the_plan_and_marks_steps_done():
    user = create_user("lena", "Passw0rd!xyz", "Lena")
    learning_service.record_quiz_attempt(user.id, "algorithms and complexity", 1, 5)
    plan = recommendation_service.get_plan(user.id)
    assert plan.steps[0].kind == "revise" and plan.steps[0].id is not None
    assert "need attention" in plan.summary
    assert recommendation_service.mark_step(user.id, plan.steps[0].id, "done")
    another = create_user("other-learner", "Passw0rd!xyz", "Other Learner")
    assert not recommendation_service.mark_step(another.id, plan.steps[0].id, "done")  # not your recommendation


def test_coach_note_uses_llm_when_available_and_degrades_gracefully(monkeypatch):
    from ai.llm_router import LLMRouter, PROVIDERS
    from services import ai_service

    user = create_user("mike", "Passw0rd!xyz", "Mike")
    learning_service.record_quiz_attempt(user.id, "statistics", 1, 5)
    assert recommendation_service.get_plan(user.id, with_ai_note=True).coach_note == ""       # offline: no note, no crash

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    ai_service.set_router(LLMRouter(PROVIDERS, transport=lambda *_: {"choices": [{"message": {"content": "Start with Statistics!"}}]}))
    assert recommendation_service.get_plan(user.id, with_ai_note=True).coach_note == "Start with Statistics!"
