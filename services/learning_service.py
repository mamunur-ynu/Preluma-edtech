"""
services/learning_service.py — the student model: record results, read the profile.

``record_quiz_attempt`` is the heart of personalisation.  In **one transaction** it:

1. stores the attempt and each mistake,
2. updates mastery for the topic, every concept that was asked, and each question type,
3. moves lesson progress (completed at ≥ 70 %),
4. awards any newly earned achievements.

Everything it needs to *decide* lives in ``core`` (pure functions); this module only loads and
saves.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from core import gamification
from core.learning_engine import (
    SKILLS_TOPIC,
    AttemptSummary,
    LearningSpeed,
    MasteryKey,
    MasteryState,
    QuestionResult,
    StreakInfo,
    StudentSnapshot,
    apply_attempt,
    infer_learning_style,
    learning_speed,
    mastery_level,
    snapshot,
    streak_info,
)
from database.connection import session_scope
from database.models import QuizAttempt, QuizMistake, SkillProfile
from database.repository import (
    AchievementRepository,
    ConversationRepository,
    EnrollmentRepository,
    LessonRepository,
    ProgressRepository,
    QuizAttemptRepository,
    SkillProfileRepository,
    UserRepository,
)
from services._common import now_utc, title_for, topic_key
from services._access import require_active_user

logger = logging.getLogger("preluma.learning")

COMPLETION_THRESHOLD = 70.0


@dataclass(frozen=True)
class AttemptOutcome:
    attempt_id: int
    topic: str
    percentage: float
    topic_mastery: float
    mastery_change: float
    new_achievements: tuple[str, ...] = ()
    lessons_completed: int = 0


@dataclass(frozen=True)
class TopicCard:
    topic: str
    title: str
    mastery: float
    level: str
    attempts: int
    trend: float
    last_practiced: datetime | None


@dataclass(frozen=True)
class StudentDashboard:
    user_id: int
    full_name: str
    overall_mastery: float
    topics: list[TopicCard]
    weak_topics: list[tuple[str, float]]
    weak_concepts: list[tuple[str, str, float]]
    weakest_skill: tuple[str, float] | None
    skill_scores: dict[str, float]
    speed: LearningSpeed
    learning_style: tuple[str, str]
    streak: StreakInfo
    xp: int
    rank: str
    rank_floor: int
    next_rank_at: int | None
    stats: dict[str, int]
    achievements: list[tuple[str, str, str]]          # (icon, title, description)
    recent_scores: list[tuple[str, str, float]]       # (iso date, topic title, percentage) oldest→newest


# ── helpers ──────────────────────────────────────────────────────────────────
def _to_state(row: SkillProfile) -> MasteryState:
    return MasteryState(
        mastery=row.mastery,
        attempts=row.attempts,
        questions_answered=row.questions_answered,
        questions_correct=row.questions_correct,
        avg_seconds_per_question=row.avg_seconds_per_question,
        previous_mastery=row.previous_mastery,
        last_practiced_at=row.last_practiced_at,
    )


def _load_profile(session, user_id: int) -> dict[MasteryKey, MasteryState]:
    return {(r.topic, r.concept): _to_state(r) for r in SkillProfileRepository(session).list_for_user(user_id)}


def get_profile(user_id: int) -> dict[MasteryKey, MasteryState]:
    """The student's mastery table: ``{(topic, concept): MasteryState}``."""
    with session_scope() as s:
        require_active_user(s, user_id)
        return _load_profile(s, user_id)


def _attempt_summary(a: QuizAttempt) -> AttemptSummary:
    return AttemptSummary(
        topic=a.topic, score=a.score, total=a.total, created_at=a.created_at,
        duration_seconds=a.duration_seconds, source=a.source,
    )


def _stats(session, user_id: int, profile: Mapping[MasteryKey, MasteryState], streak: StreakInfo) -> dict[str, int]:
    attempts = QuizAttemptRepository(session).list_for_user(user_id)
    convo = ConversationRepository(session).recent_user_messages(user_id, limit=1000)
    progress = ProgressRepository(session).list_for_user(user_id)
    topic_states = [s for (t, c), s in profile.items() if c == "" and t != SKILLS_TOPIC]
    return {
        "attempts": len(attempts),
        "perfect_scores": sum(1 for a in attempts if a.total > 0 and a.score == a.total),
        "lessons_completed": sum(1 for p in progress if p.status == "completed"),
        "ai_questions": len(convo),
        "streak": streak.current,
        "longest_streak": streak.longest,
        "distinct_topics": len({a.topic for a in attempts}),
        "topics_mastered": sum(1 for s in topic_states if s.mastery >= 80),
    }


def _activity_days(session, user_id: int):
    days = []
    days += QuizAttemptRepository(session).activity_dates(user_id)
    days += ConversationRepository(session).activity_dates(user_id)
    days += ProgressRepository(session).completed_dates(user_id)
    return days


# ── write path ───────────────────────────────────────────────────────────────
def record_quiz_attempt(
    user_id: int,
    topic: str,
    score: int,
    total: int,
    *,
    duration_seconds: int = 0,
    source: str = "mission",
    learning_mode: str = "",
    details: Sequence[Mapping[str, object]] = (),
    when: datetime | None = None,
    course_id: int | None = None,
) -> AttemptOutcome:
    """Store one quiz attempt and update everything derived from it.

    ``details`` is the per-question list returned by ``core.assessment_engine.grade`` (keys
    ``correct``, ``skill``, ``concept``, ``q``, ``chosen``, ``answer``); homework passes the
    same shape.  ``topic`` may be a title, alias or canonical key.
    """
    if total <= 0:
        raise ValueError("A quiz needs at least one question.")
    score = max(0, min(int(score), int(total)))
    key = topic_key(topic)
    now = when or now_utc()

    results = tuple(
        QuestionResult(
            correct=bool(d.get("correct")),
            skill=str(d.get("skill") or ""),
            concept=str(d.get("concept") or ""),
        )
        for d in details
    )
    mistakes = [
        QuizMistake(
            topic=key,
            skill=str(d.get("skill") or ""),
            concept=str(d.get("concept") or ""),
            question=str(d.get("q") or d.get("question") or "")[:2000],
            student_answer=str(d.get("chosen") or "")[:2000],
            correct_answer=str(d.get("answer") or d.get("correct_answer") or "")[:2000],
        )
        for d in details
        if not d.get("correct")
    ]

    with session_scope() as s:
        require_active_user(s, user_id)
        enrolled = set(EnrollmentRepository(s).course_ids_for_user(user_id))
        matching_lessons = list(LessonRepository(s).find_by_topic(key))
        matching_courses = {lesson.course_id for lesson in matching_lessons} & enrolled
        if course_id is not None:
            if course_id not in matching_courses:
                raise PermissionError("The topic is not in an enrolled course.")
        elif len(matching_courses) == 1:
            course_id = next(iter(matching_courses))
        lesson_id = next((lesson.id for lesson in matching_lessons if lesson.course_id == course_id), None)
        attempt = QuizAttemptRepository(s).add(
            QuizAttempt(
                user_id=user_id, course_id=course_id, lesson_id=lesson_id, topic=key,
                source=source, score=score, total=total,
                percentage=round(100.0 * score / total, 1), duration_seconds=max(0, int(duration_seconds)),
                learning_mode=learning_mode[:32], created_at=now,
            ),
            mistakes,
        )
        from services.learning_events import append_quiz_event, rebuild_course_mastery

        append_quiz_event(s, attempt)
        if attempt.course_id is not None:
            rebuild_course_mastery(s, user_id, attempt.course_id)

        profile = _load_profile(s, user_id)
        before = profile.get((key, ""), MasteryState()).mastery
        summary = AttemptSummary(key, score, total, now, int(duration_seconds), source, results)
        updated = apply_attempt(profile, summary)
        skills = SkillProfileRepository(s)
        for (topic_name, concept), state in updated.items():
            row = skills.get_or_create(user_id, topic_name, concept)
            row.mastery = state.mastery
            row.attempts = state.attempts
            row.questions_answered = state.questions_answered
            row.questions_correct = state.questions_correct
            row.avg_seconds_per_question = state.avg_seconds_per_question
            row.previous_mastery = state.previous_mastery
            row.last_practiced_at = state.last_practiced_at
        profile.update(updated)
        after = updated[(key, "")].mastery

        # Lessons for this topic in the student's enrolled courses move forward.
        completed_now = 0
        for lesson in matching_lessons:
            if course_id is None:
                continue  # ambiguous/direct practice must not complete multiple courses
            if lesson.course_id not in enrolled:
                continue
            if lesson.course_id != course_id:
                continue
            done = attempt.percentage >= COMPLETION_THRESHOLD
            ProgressRepository(s).upsert(
                user_id, lesson.id,
                status="completed" if done else "in_progress",
                percent=100.0 if done else attempt.percentage,
                add_seconds=duration_seconds,
            )
            completed_now += int(done)

        streak = streak_info(_activity_days(s, user_id), now.date())
        stats = _stats(s, user_id, profile, streak)
        achievements = AchievementRepository(s)
        earned = []
        for definition in gamification.evaluate_achievements(stats, achievements.codes_for_user(user_id)):
            if achievements.award(user_id, definition.code, definition.title, definition.description):
                earned.append(definition.code)

        return AttemptOutcome(
            attempt_id=attempt.id, topic=key, percentage=attempt.percentage,
            topic_mastery=after, mastery_change=round(after - before, 1),
            new_achievements=tuple(earned), lessons_completed=completed_now,
        )


def record_mission_result(
    user_id: int, topic: str, grade_result: Mapping[str, object], *,
    learning_mode: str = "", duration_seconds: int = 0, source: str = "mission",
    course_id: int | None = None,
) -> AttemptOutcome:
    """Convenience wrapper for the dict returned by ``core.assessment_engine.grade``."""
    return record_quiz_attempt(
        user_id, topic, int(grade_result["score"]), int(grade_result["total"]),
        duration_seconds=duration_seconds, source=source, learning_mode=learning_mode,
        course_id=course_id,
        details=grade_result.get("details", []),  # type: ignore[arg-type]
    )


# ── read path ────────────────────────────────────────────────────────────────
def get_snapshot(user_id: int) -> StudentSnapshot:
    return snapshot(get_profile(user_id))


def style_signals(user_id: int) -> tuple[list[str], list[str]]:
    """(question styles from AI chat, learning modes from attempts) — inputs for style inference."""
    with session_scope() as s:
        require_active_user(s, user_id)
        styles = [m.question_style for m in ConversationRepository(s).recent_user_messages(user_id, 200) if m.question_style]
        modes = [a.learning_mode for a in QuizAttemptRepository(s).list_for_user(user_id, limit=200) if a.learning_mode]
    return styles, modes


def get_dashboard(user_id: int) -> StudentDashboard:
    """Everything the student dashboard shows, computed in one call."""
    now = now_utc()
    with session_scope() as s:
        user = require_active_user(s, user_id)
        profile = _load_profile(s, user_id)
        attempts = list(QuizAttemptRepository(s).list_for_user(user_id))
        streak = streak_info(_activity_days(s, user_id), now.date())
        stats = _stats(s, user_id, profile, streak)
        owned = AchievementRepository(s).list_for_user(user_id)
        full_name = user.full_name
        stored_style = user.preferred_learning_style

    snap = snapshot(profile)
    cards = sorted(
        (
            TopicCard(t, title_for(t), st.mastery, mastery_level(st.mastery), st.attempts, st.trend, st.last_practiced_at)
            for t, st in snap.topic_mastery.items()
        ),
        key=lambda c: c.mastery,
    )
    skill_scores = {c: st.mastery for (t, c), st in profile.items() if t == SKILLS_TOPIC and st.attempts > 0}
    styles, modes = style_signals(user_id)
    inferred = infer_learning_style(styles, modes)
    xp = gamification.compute_xp(stats)
    rank, rank_floor, next_at = gamification.rank_for_xp(xp)
    badge_info = []
    for row in owned:
        definition = gamification.get_achievement(row.code)
        badge_info.append((definition.icon if definition else "🏆", row.title, row.description))
    chronological = sorted(attempts, key=lambda a: (a.created_at, a.id))[-12:]
    return StudentDashboard(
        user_id=user_id,
        full_name=full_name,
        overall_mastery=snap.overall_mastery,
        topics=cards,
        weak_topics=[(title_for(t), m) for t, m in snap.weak_topics],
        weak_concepts=[(title_for(t), c, m) for t, c, m in snap.weak_concepts],
        weakest_skill=snap.weakest_skill,
        skill_scores=skill_scores,
        speed=learning_speed([_attempt_summary(a) for a in attempts]),
        learning_style=(stored_style, stored_style) if stored_style else inferred,
        streak=streak,
        xp=xp, rank=rank, rank_floor=rank_floor, next_rank_at=next_at,
        stats=stats,
        achievements=badge_info,
        recent_scores=[(a.created_at.strftime("%b %d"), title_for(a.topic), a.percentage) for a in chronological],
    )


def recent_mistakes(user_id: int, limit: int = 10) -> list[dict[str, str]]:
    with session_scope() as s:
        require_active_user(s, user_id)
        return [
            {"topic": title_for(m.topic), "concept": m.concept, "skill": m.skill, "question": m.question,
             "your_answer": m.student_answer, "correct_answer": m.correct_answer}
            for m in QuizAttemptRepository(s).mistakes_for_user(user_id, limit)
        ]


def set_learning_style(user_id: int, style: str | None) -> None:
    with session_scope() as s:
        repo = UserRepository(s)
        user = require_active_user(s, user_id)
        repo.set_learning_style(user, style or None)


__all__ = [
    "AttemptOutcome", "StudentDashboard", "TopicCard", "COMPLETION_THRESHOLD",
    "get_dashboard", "get_profile", "get_snapshot", "recent_mistakes", "record_mission_result",
    "record_quiz_attempt", "set_learning_style", "style_signals",
]
