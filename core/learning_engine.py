"""
core/learning_engine.py — turns quiz results into a model of the student.

Pure Python, standard library only, no I/O: give it attempts, get back mastery, weak
topics, learning speed, learning style and streaks.  Services load the data from the
database, call these functions and persist the results.

Mastery model
-------------
Mastery (0–100) is an exponentially weighted average of the student's accuracy:

* the first observation is shrunk towards 50 % by one "virtual" question (a single lucky
  answer must not look like expertise);
* later observations move the estimate by ``alpha = max(0.3, 1/(n+1))`` — early attempts
  matter a lot, recent attempts always keep at least 30 % influence;
* small samples (few questions) move the estimate less than full quizzes.

Mastery is tracked at three levels, all stored in ``skill_profiles``:
``(topic, "")`` topic aggregate · ``(topic, concept)`` concept · ``("_skills", skill)``
question-type skill such as *Application*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, Mapping, Sequence

SKILLS_TOPIC = "_skills"          # sentinel "topic" that holds question-type mastery rows
WEAK_THRESHOLD = 60.0
STRONG_THRESHOLD = 75.0
PRIOR_MASTERY = 50.0
PRIOR_WEIGHT = 1.0

MasteryKey = tuple[str, str]      # (topic, concept)


@dataclass(frozen=True)
class QuestionResult:
    """Outcome of one question inside an attempt."""

    correct: bool
    skill: str = ""               # Definition / Core Concept / Application / Misconception
    concept: str = ""


@dataclass(frozen=True)
class AttemptSummary:
    """Everything the engine needs to know about one quiz attempt."""

    topic: str
    score: int
    total: int
    created_at: datetime
    duration_seconds: int = 0
    source: str = "mission"
    results: tuple[QuestionResult, ...] = ()

    @property
    def percentage(self) -> float:
        return 100.0 * self.score / self.total if self.total > 0 else 0.0


@dataclass(frozen=True)
class MasteryState:
    """Mastery estimate for one :data:`MasteryKey`."""

    mastery: float = 0.0
    attempts: int = 0
    questions_answered: int = 0
    questions_correct: int = 0
    avg_seconds_per_question: float = 0.0
    previous_mastery: float = 0.0
    last_practiced_at: datetime | None = None

    @property
    def trend(self) -> float:
        """Change in mastery caused by the most recent update (positive = improving)."""
        return round(self.mastery - self.previous_mastery, 1) if self.attempts > 1 else 0.0

    @property
    def accuracy(self) -> float:
        return 100.0 * self.questions_correct / self.questions_answered if self.questions_answered else 0.0


# ── mastery updates ──────────────────────────────────────────────────────────
def update_mastery(
    state: MasteryState,
    correct: int,
    total: int,
    seconds: float = 0.0,
    when: datetime | None = None,
) -> MasteryState:
    """Fold ``correct`` out of ``total`` answers into ``state`` and return the new state."""
    if total <= 0:
        return state
    correct = max(0, min(correct, total))
    pct = 100.0 * correct / total
    if state.attempts == 0:
        new_mastery = (pct * total + PRIOR_MASTERY * PRIOR_WEIGHT) / (total + PRIOR_WEIGHT)
    else:
        alpha = max(0.3, 1.0 / (state.attempts + 1)) * (total / (total + PRIOR_WEIGHT))
        new_mastery = state.mastery + alpha * (pct - state.mastery)

    answered = state.questions_answered + total
    avg_seconds = state.avg_seconds_per_question
    if seconds > 0:
        avg_seconds = (avg_seconds * state.questions_answered + seconds) / answered

    return MasteryState(
        mastery=round(max(0.0, min(100.0, new_mastery)), 2),
        attempts=state.attempts + 1,
        questions_answered=answered,
        questions_correct=state.questions_correct + correct,
        avg_seconds_per_question=round(avg_seconds, 2),
        previous_mastery=state.mastery,
        last_practiced_at=when or state.last_practiced_at,
    )


def apply_attempt(
    profile: Mapping[MasteryKey, MasteryState], attempt: AttemptSummary
) -> dict[MasteryKey, MasteryState]:
    """Return the *updated* entries (topic, per-concept and per-skill) caused by ``attempt``.

    The input mapping is not modified; the caller persists the returned entries.
    """
    updated: dict[MasteryKey, MasteryState] = {}
    when = attempt.created_at

    topic_key = (attempt.topic, "")
    updated[topic_key] = update_mastery(
        profile.get(topic_key, MasteryState()), attempt.score, attempt.total, attempt.duration_seconds, when
    )

    per_concept: dict[str, list[bool]] = {}
    per_skill: dict[str, list[bool]] = {}
    for result in attempt.results:
        if result.concept:
            per_concept.setdefault(result.concept, []).append(result.correct)
        if result.skill:
            per_skill.setdefault(result.skill, []).append(result.correct)

    for concept, outcomes in per_concept.items():
        key = (attempt.topic, concept)
        updated[key] = update_mastery(profile.get(key, MasteryState()), sum(outcomes), len(outcomes), 0, when)
    for skill, outcomes in per_skill.items():
        key = (SKILLS_TOPIC, skill)
        updated[key] = update_mastery(profile.get(key, MasteryState()), sum(outcomes), len(outcomes), 0, when)
    return updated


def decayed_mastery(state: MasteryState, now: datetime, half_life_days: float = 30.0) -> float:
    """Mastery after forgetting: drifts towards 50 with the given half-life (never to zero)."""
    if state.last_practiced_at is None:
        return state.mastery
    days = max(0.0, (now - state.last_practiced_at).total_seconds() / 86400.0)
    factor = 0.5 ** (days / half_life_days)
    return round(PRIOR_MASTERY + (state.mastery - PRIOR_MASTERY) * factor, 2)


def mastery_level(mastery: float) -> str:
    """Friendly skill level used on cards and charts."""
    if mastery >= 85:
        return "Expert"
    if mastery >= STRONG_THRESHOLD:
        return "Proficient"
    if mastery >= WEAK_THRESHOLD:
        return "Developing"
    if mastery >= 35:
        return "Novice"
    return "Beginner"


# ── weaknesses ───────────────────────────────────────────────────────────────
def weak_topics(
    profile: Mapping[MasteryKey, MasteryState], threshold: float = WEAK_THRESHOLD
) -> list[tuple[str, float]]:
    """``[(topic, mastery)]`` for topic aggregates below ``threshold``, weakest first."""
    rows = [
        (topic, state.mastery)
        for (topic, concept), state in profile.items()
        if concept == "" and topic != SKILLS_TOPIC and state.attempts > 0 and state.mastery < threshold
    ]
    return sorted(rows, key=lambda item: item[1])


def weak_concepts(
    profile: Mapping[MasteryKey, MasteryState], topic: str | None = None, threshold: float = WEAK_THRESHOLD
) -> list[tuple[str, str, float]]:
    """``[(topic, concept, mastery)]`` below ``threshold``, weakest first (optionally one topic)."""
    rows = [
        (t, c, state.mastery)
        for (t, c), state in profile.items()
        if c and t != SKILLS_TOPIC and (topic is None or t == topic)
        and state.attempts > 0 and state.mastery < threshold
    ]
    return sorted(rows, key=lambda item: item[2])


def weakest_skill(profile: Mapping[MasteryKey, MasteryState]) -> tuple[str, float] | None:
    """The question type (e.g. *Application*) the student answers worst, if measured."""
    rows = [(c, s.mastery) for (t, c), s in profile.items() if t == SKILLS_TOPIC and s.attempts > 0]
    return min(rows, key=lambda item: item[1]) if rows else None


# ── learning speed ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LearningSpeed:
    avg_seconds_per_question: float
    improvement_per_attempt: float   # percentage points gained per attempt (regression slope)
    label: str
    pace: str                        # fast | steady | careful | unknown


def slope(values: Sequence[float]) -> float:
    """Least-squares slope of ``values`` against 0, 1, 2 … (0.0 if fewer than two points)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    return sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values)) / denominator


def learning_speed(attempts: Sequence[AttemptSummary]) -> LearningSpeed:
    """Estimate how quickly the student answers and how quickly they improve.

    ``attempts`` may be in any order; they are sorted by time here.
    """
    ordered = sorted(attempts, key=lambda a: a.created_at)
    timed = [a for a in ordered if a.duration_seconds > 0 and a.total > 0]
    seconds = sum(a.duration_seconds for a in timed)
    questions = sum(a.total for a in timed)
    avg = seconds / questions if questions else 0.0
    gain = slope([a.percentage for a in ordered])

    if not timed:
        pace = "unknown"
    elif avg < 20:
        pace = "fast"
    elif avg <= 60:
        pace = "steady"
    else:
        pace = "careful"

    if len(ordered) < 2:
        label = "Not enough data yet"
    elif gain >= 3:
        label = "Fast improver"
    elif gain >= 0.5:
        label = "Steady improver"
    elif gain > -0.5:
        label = "Holding level"
    else:
        label = "Needs support"
    return LearningSpeed(round(avg, 1), round(gain, 2), label, pace)


# ── learning style ───────────────────────────────────────────────────────────
STYLE_LABELS = {
    "example": "Learns by examples",
    "child": "Prefers simple explanations",
    "exam": "Exam-focused",
    "deep": "Likes deep, step-by-step reasoning",
    "compare": "Thinks by comparing ideas",
}
_MODE_TO_STYLE = {
    "Fast Review": "child",
    "Deep Understanding": "deep",
    "Exam/Viva Mode": "exam",
}


def infer_learning_style(
    question_styles: Iterable[str] = (), learning_modes: Iterable[str] = (), minimum_signals: int = 3
) -> tuple[str, str]:
    """Infer ``(style_key, label)`` from how the student *asks* and which mission modes they pick.

    ``question_styles`` are the styles the AI service detected in the student's chat questions
    (``child/example/exam/compare/deep/normal``).  Returns ``("unknown", ...)`` until there are
    at least ``minimum_signals`` informative signals.
    """
    counts: dict[str, int] = {}
    for style in question_styles:
        if style in STYLE_LABELS:
            counts[style] = counts.get(style, 0) + 1
    for mode in learning_modes:
        mapped = _MODE_TO_STYLE.get(mode)
        if mapped:
            counts[mapped] = counts.get(mapped, 0) + 1
    if sum(counts.values()) < minimum_signals:
        return "unknown", "Not enough data yet — ask the AI tutor a few questions"
    best = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return best, STYLE_LABELS[best]


# ── streaks ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StreakInfo:
    current: int
    longest: int
    active_today: bool


def streak_info(days: Iterable[date], today: date) -> StreakInfo:
    """Consecutive-day streaks.  A streak stays alive until the end of the day after the last activity."""
    unique = sorted(set(days))
    if not unique:
        return StreakInfo(0, 0, False)

    longest = run = 1
    for previous, current in zip(unique, unique[1:]):
        run = run + 1 if (current - previous).days == 1 else 1
        longest = max(longest, run)

    last = unique[-1]
    active_today = last == today
    alive = (today - last).days <= 1
    current_streak = 0
    if alive:
        current_streak = 1
        for idx in range(len(unique) - 1, 0, -1):
            if (unique[idx] - unique[idx - 1]).days == 1:
                current_streak += 1
            else:
                break
    return StreakInfo(current_streak, longest, active_today)


# ── overall profile snapshot ─────────────────────────────────────────────────
@dataclass(frozen=True)
class StudentSnapshot:
    """Computed view used by the dashboard and the recommendation engine."""

    topic_mastery: dict[str, MasteryState] = field(default_factory=dict)
    weak_topics: tuple[tuple[str, float], ...] = ()
    weak_concepts: tuple[tuple[str, str, float], ...] = ()
    weakest_skill: tuple[str, float] | None = None
    overall_mastery: float = 0.0


def snapshot(profile: Mapping[MasteryKey, MasteryState]) -> StudentSnapshot:
    topics = {
        t: s for (t, c), s in profile.items() if c == "" and t != SKILLS_TOPIC and s.attempts > 0
    }
    overall = sum(s.mastery for s in topics.values()) / len(topics) if topics else 0.0
    return StudentSnapshot(
        topic_mastery=topics,
        weak_topics=tuple(weak_topics(profile)),
        weak_concepts=tuple(weak_concepts(profile)),
        weakest_skill=weakest_skill(profile),
        overall_mastery=round(overall, 1),
    )


def days_ago(now: datetime, days: int) -> datetime:
    """Tiny helper that keeps tests readable."""
    return now - timedelta(days=days)
