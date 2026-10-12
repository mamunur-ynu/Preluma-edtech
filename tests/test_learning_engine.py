"""Pure-Python learning engine: mastery, weaknesses, speed, style, streaks, gamification."""

from datetime import date, datetime, timedelta

from core import gamification
from core.learning_engine import (
    AttemptSummary, MasteryState, QuestionResult, apply_attempt, decayed_mastery, infer_learning_style,
    learning_speed, mastery_level, snapshot, streak_info, update_mastery, weak_concepts, weak_topics,
)

NOW = datetime(2026, 1, 10, 12, 0)


def test_first_attempt_is_shrunk_towards_the_prior():
    state = update_mastery(MasteryState(), 5, 5)
    assert 50 < state.mastery < 100                      # a perfect first quiz is not instantly "100% mastered"
    assert update_mastery(MasteryState(), 0, 5).mastery > 0


def test_mastery_moves_towards_new_evidence_and_stays_in_range():
    state = MasteryState()
    for _ in range(8):
        state = update_mastery(state, 5, 5)
    assert state.mastery > 85
    for _ in range(8):
        state = update_mastery(state, 0, 5)
    assert 0 <= state.mastery < 40 and state.trend <= 0


def test_zero_questions_changes_nothing():
    state = update_mastery(MasteryState(), 3, 4)
    assert update_mastery(state, 0, 0) == state


def test_apply_attempt_updates_topic_concept_and_skill_levels():
    attempt = AttemptSummary("python programming", 2, 4, NOW, results=(
        QuestionResult(True, "Definition", "variables"), QuestionResult(True, "Application", "loops"),
        QuestionResult(False, "Application", "loops"), QuestionResult(False, "Misconception", "variables")))
    updated = apply_attempt({}, attempt)
    assert ("python programming", "") in updated
    assert ("python programming", "loops") in updated
    assert ("_skills", "Application") in updated


def test_weak_topics_and_concepts_are_sorted_weakest_first():
    profile = {
        ("a", ""): MasteryState(mastery=40, attempts=2), ("b", ""): MasteryState(mastery=55, attempts=1),
        ("c", ""): MasteryState(mastery=90, attempts=3), ("a", "x"): MasteryState(mastery=30, attempts=1),
    }
    assert [t for t, _ in weak_topics(profile)] == ["a", "b"]
    assert weak_concepts(profile)[0][:2] == ("a", "x")
    snap = snapshot(profile)
    assert 0 < snap.overall_mastery < 100


def test_forgetting_curve_pulls_towards_fifty():
    state = MasteryState(mastery=90, attempts=3, last_practiced_at=NOW - timedelta(days=30))
    assert 65 < decayed_mastery(state, NOW) < 75          # half-life of 30 days
    assert decayed_mastery(state, NOW - timedelta(days=30)) == 90


def test_mastery_levels():
    assert [mastery_level(v) for v in (10, 40, 65, 80, 95)] == ["Beginner", "Novice", "Developing", "Proficient", "Expert"]


def test_learning_speed_detects_improvement_and_pace():
    attempts = [AttemptSummary("t", s, 5, NOW + timedelta(days=i), duration_seconds=100)
                for i, s in enumerate([1, 2, 3, 4, 5])]
    speed = learning_speed(attempts)
    assert speed.label == "Fast improver" and speed.pace == "steady" and speed.improvement_per_attempt > 3
    assert learning_speed([]).label == "Not enough data yet"


def test_learning_style_needs_enough_signals():
    assert infer_learning_style(["example"])[0] == "unknown"
    assert infer_learning_style(["example", "example", "exam"])[0] == "example"
    assert infer_learning_style([], ["Exam/Viva Mode"] * 3)[0] == "exam"


def test_streaks():
    today = date(2026, 1, 10)
    days = [today - timedelta(days=n) for n in (0, 1, 2, 5)]
    info = streak_info(days, today)
    assert (info.current, info.longest, info.active_today) == (3, 3, True)
    assert streak_info([today - timedelta(days=1)], today).current == 1       # still alive until tonight
    assert streak_info([today - timedelta(days=3)], today).current == 0
    assert streak_info([], today).longest == 0


def test_gamification_ranks_and_achievements():
    assert gamification.rank_for_xp(0)[0] == "Beginner"
    assert gamification.rank_for_xp(1500)[0] == "Master"
    stats = {"attempts": 1, "perfect_scores": 1}
    earned = {a.code for a in gamification.evaluate_achievements(stats, set())}
    assert "first_quiz" in earned
    assert "first_quiz" not in {a.code for a in gamification.evaluate_achievements(stats, {"first_quiz"})}
