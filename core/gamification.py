"""
core/gamification.py — XP, ranks and achievements (pure Python, no I/O).

Everything is derived from a plain ``stats`` dict, so the same rules work for any front end:

    stats = {"attempts": 4, "perfect_scores": 1, "lessons_completed": 3, "ai_questions": 7,
             "streak": 3, "longest_streak": 5, "distinct_topics": 3, "topics_mastered": 1}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

Stats = Mapping[str, int]

# Five-tier rank system that already existed in the app (Beginner → Master).
RANKS = (
    (0, "Beginner"),
    (100, "Explorer"),
    (300, "Achiever"),
    (700, "Scholar"),
    (1500, "Master"),
)


@dataclass(frozen=True)
class AchievementDef:
    code: str
    title: str
    description: str
    icon: str
    earned: Callable[[Stats], bool]


ACHIEVEMENTS: tuple[AchievementDef, ...] = (
    AchievementDef("first_quiz", "First Steps", "Complete your first quiz.", "🚀",
                   lambda s: s.get("attempts", 0) >= 1),
    AchievementDef("ten_quizzes", "Quiz Machine", "Complete 10 quizzes.", "🏅",
                   lambda s: s.get("attempts", 0) >= 10),
    AchievementDef("perfect_score", "Flawless", "Score 100 % on a quiz.", "💯",
                   lambda s: s.get("perfect_scores", 0) >= 1),
    AchievementDef("streak_3", "On a Roll", "Learn 3 days in a row.", "🔥",
                   lambda s: max(s.get("streak", 0), s.get("longest_streak", 0)) >= 3),
    AchievementDef("streak_7", "Unstoppable", "Learn 7 days in a row.", "⚡",
                   lambda s: max(s.get("streak", 0), s.get("longest_streak", 0)) >= 7),
    AchievementDef("first_mastery", "Topic Master", "Reach 80 % mastery in a topic.", "🎓",
                   lambda s: s.get("topics_mastered", 0) >= 1),
    AchievementDef("explorer", "Explorer", "Practise 5 different topics.", "🧭",
                   lambda s: s.get("distinct_topics", 0) >= 5),
    AchievementDef("curious", "Curious Mind", "Ask the AI tutor 10 questions.", "💬",
                   lambda s: s.get("ai_questions", 0) >= 10),
    AchievementDef("lesson_finisher", "Finisher", "Complete 5 lessons.", "✅",
                   lambda s: s.get("lessons_completed", 0) >= 5),
)
_BY_CODE = {a.code: a for a in ACHIEVEMENTS}


def compute_xp(stats: Stats) -> int:
    """Experience points: attempts, perfect scores, lessons, tutor questions and streak."""
    return (
        stats.get("attempts", 0) * 10
        + stats.get("perfect_scores", 0) * 20
        + stats.get("lessons_completed", 0) * 15
        + stats.get("ai_questions", 0) * 2
        + min(stats.get("streak", 0), 30) * 5
    )


def rank_for_xp(xp: int) -> tuple[str, int, int | None]:
    """``(rank name, xp needed for this rank, xp needed for the next rank or None)``."""
    current = RANKS[0]
    next_threshold: int | None = None
    for index, (threshold, name) in enumerate(RANKS):
        if xp >= threshold:
            current = (threshold, name)
            next_threshold = RANKS[index + 1][0] if index + 1 < len(RANKS) else None
    return current[1], current[0], next_threshold


def evaluate_achievements(stats: Stats, already_earned: set[str]) -> list[AchievementDef]:
    """Achievements the student qualifies for that they do not own yet."""
    return [a for a in ACHIEVEMENTS if a.code not in already_earned and a.earned(stats)]


def get_achievement(code: str) -> AchievementDef | None:
    return _BY_CODE.get(code)
