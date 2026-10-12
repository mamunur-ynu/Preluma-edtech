"""
services/analytics_service.py — class-level analytics for the teacher dashboard.

Reads the relational data (attempts, skill profiles, progress), delegates the arithmetic to
``core.analytics_engine`` and returns plain structures ready for charts and tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from core.analytics_engine import completion_rate, readiness_label, score_distribution, topic_difficulty_ranking
from core.learning_engine import SKILLS_TOPIC, mastery_level
from database.connection import session_scope
from database.models import ROLE_STUDENT
from database.repository import (
    EnrollmentRepository,
    LessonRepository,
    ProgressRepository,
    QuizAttemptRepository,
    SkillProfileRepository,
    UserRepository,
)
from services._common import now_utc, title_for


@dataclass(frozen=True)
class StudentRow:
    user_id: int
    name: str
    username: str
    overall_mastery: float
    label: str
    attempts: int
    last_active: str
    weak_topics: tuple[str, ...]


@dataclass
class ClassOverview:
    students: int = 0
    active_last_7_days: int = 0
    average_mastery: float = 0.0
    average_quiz_score: float = 0.0
    completion_rate: float = 0.0
    distribution: list[dict] = field(default_factory=list)
    topic_ranking: list[dict] = field(default_factory=list)       # hardest first
    daily_scores: list[dict] = field(default_factory=list)        # {"day","average","attempts"}
    top_mistakes: list[dict] = field(default_factory=list)        # {"topic","concept","count"}
    student_rows: list[StudentRow] = field(default_factory=list)


def class_overview(course_id: int | None = None, days: int = 30) -> ClassOverview:
    """Aggregate view of the class (or of one course's enrolled students)."""
    now = now_utc()
    with session_scope() as s:
        users = UserRepository(s)
        roster = [u for u in users.list_by_role(ROLE_STUDENT) if u.is_active]
        if course_id is not None:
            enrolled = set(EnrollmentRepository(s).user_ids_for_course(course_id))
            roster = [u for u in roster if u.id in enrolled]
        ids = {u.id for u in roster}
        overview = ClassOverview(students=len(roster))
        if not roster:
            return overview

        skills = [r for r in SkillProfileRepository(s).list_topic_level() if r.user_id in ids and r.topic != SKILLS_TOPIC and r.attempts > 0]
        per_student: dict[int, list] = {}
        for row in skills:
            per_student.setdefault(row.user_id, []).append(row)

        attempts = [a for a in QuizAttemptRepository(s).all_recent(days) if a.user_id in ids]
        attempts_by_user: dict[int, list] = {}
        for a in attempts:
            attempts_by_user.setdefault(a.user_id, []).append(a)

        weekly_cutoff = now - timedelta(days=7)
        overview.active_last_7_days = len({a.user_id for a in attempts if a.created_at >= weekly_cutoff})

        rows = []
        for u in roster:
            mine = per_student.get(u.id, [])
            overall = sum(r.mastery for r in mine) / len(mine) if mine else 0.0
            last = max((a.created_at for a in attempts_by_user.get(u.id, [])), default=None)
            weak = tuple(title_for(r.topic) for r in sorted(mine, key=lambda r: r.mastery) if r.mastery < 60)[:3]
            rows.append(StudentRow(
                user_id=u.id, name=u.full_name, username=u.username, overall_mastery=round(overall, 1),
                label=readiness_label(overall) if mine else "No data yet", attempts=len(attempts_by_user.get(u.id, [])),
                last_active=last.strftime("%Y-%m-%d") if last else "—", weak_topics=weak,
            ))
        overview.student_rows = sorted(rows, key=lambda r: r.overall_mastery)

        measured = [r.overall_mastery for r in rows if r.attempts or r.overall_mastery]
        overview.average_mastery = round(sum(measured) / len(measured), 1) if measured else 0.0
        overview.average_quiz_score = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0.0
        overview.distribution = score_distribution(r.overall_mastery for r in rows if r.attempts)
        overview.topic_ranking = [
            {**item, "title": title_for(item["topic"])}
            for item in topic_difficulty_ranking({"topic": r.topic, "mastery": r.mastery} for r in skills)
        ]

        by_day: dict[str, list[float]] = {}
        for a in attempts:
            by_day.setdefault(a.created_at.strftime("%Y-%m-%d"), []).append(a.percentage)
        overview.daily_scores = [
            {"day": day, "average": round(sum(v) / len(v), 1), "attempts": len(v)} for day, v in sorted(by_day.items())
        ]
        overview.top_mistakes = [
            {"topic": title_for(t), "concept": c or "(general)", "count": n}
            for t, c, n in QuizAttemptRepository(s).mistake_counts_by_concept()[:8]
        ]

        # completion: share of lessons completed across the roster's enrolled courses
        total_lessons = done_lessons = 0
        for u in roster:
            for cid in EnrollmentRepository(s).course_ids_for_user(u.id):
                if course_id is not None and cid != course_id:
                    continue
                lesson_ids = [lesson.id for lesson in LessonRepository(s).list_for_course(cid)]
                total_lessons += len(lesson_ids)
                done_lessons += sum(1 for p in ProgressRepository(s).list_for_lessons(u.id, lesson_ids) if p.status == "completed")
        overview.completion_rate = completion_rate(done_lessons, total_lessons)
        return overview


def student_detail(user_id: int) -> dict:
    """Mastery table for one student (teacher drill-down)."""
    with session_scope() as s:
        rows = [r for r in SkillProfileRepository(s).list_for_user(user_id) if r.concept == "" and r.topic != SKILLS_TOPIC]
        return {
            "topics": [
                {"topic": title_for(r.topic), "mastery": r.mastery, "level": mastery_level(r.mastery),
                 "attempts": r.attempts, "trend": round(r.mastery - r.previous_mastery, 1) if r.attempts > 1 else 0.0}
                for r in sorted(rows, key=lambda r: r.mastery)
            ]
        }
