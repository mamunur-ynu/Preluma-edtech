"""
services/course_service.py — courses, lessons, enrolment and progress.

The catalogue is *derived from the curated topic library*: each lesson points at a topic pack
(``topic_key``) so the existing Mission flow (brief → examples → quiz → mock test) is the
content of every lesson.  Teachers can create additional courses and lessons.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analytics_engine import completion_rate
from core.knowledge_graph import build_graph
from core.topics import TOPICS
from database.connection import session_scope
from database.models import Course, Lesson
from database.repository import (
    CourseRepository,
    EnrollmentRepository,
    LessonRepository,
    ProgressRepository,
    UserRepository,
)
from services._common import title_for, topic_key

# Default catalogue: slug -> (title, description, level, topic keys)
DEFAULT_COURSES: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "programming-foundations": (
        "Programming Foundations",
        "From Python basics to data structures, algorithms and professional software practice.",
        "Beginner",
        ("python programming", "data structures", "algorithms and complexity", "software engineering",
         "api development", "devops"),
    ),
    "ai-and-machine-learning": (
        "AI & Machine Learning",
        "Statistics-backed path from regression to neural networks, vision, language and reinforcement learning.",
        "Intermediate",
        ("artificial intelligence", "machine learning", "linear regression", "logistic regression",
         "decision tree", "neural network", "convolutional neural network", "computer vision",
         "natural language processing", "reinforcement learning"),
    ),
    "computing-systems": (
        "Computing Systems",
        "Operating systems, networks, databases and the cloud — how real systems fit together.",
        "Intermediate",
        ("operating system", "computer network", "database management system", "cloud computing",
         "cybersecurity", "big data", "internet of things", "blockchain"),
    ),
    "science-and-society": (
        "Science & Society",
        "Statistics, quantum ideas and urban water management: science applied to the world.",
        "Beginner",
        ("statistics", "quantum mechanics", "quantum computing", "urban water management"),
    ),
}


@dataclass(frozen=True)
class LessonView:
    id: int
    title: str
    topic_key: str
    order_index: int
    estimated_minutes: int
    difficulty: str
    status: str = "not_started"
    percent: float = 0.0
    locked_by: tuple[str, ...] = ()        # titles of unmet prerequisite topics (informational)


@dataclass(frozen=True)
class CourseView:
    id: int
    slug: str
    title: str
    description: str
    level: str
    lesson_count: int
    enrolled: bool = False
    completed_lessons: int = 0
    percent: float = 0.0
    lessons: list[LessonView] = field(default_factory=list)


# ── catalogue ────────────────────────────────────────────────────────────────
def _ordered_topics(keys: tuple[str, ...]) -> list[str]:
    """Order topics so prerequisites come first (stable topological sort)."""
    graph = build_graph()
    remaining = [k for k in keys if k in TOPICS]
    ordered: list[str] = []
    while remaining:
        progressed = False
        for key in list(remaining):
            prereqs = [p for p in (graph[key].prerequisites if key in graph else ()) if p in keys]
            if all(p in ordered for p in prereqs):
                ordered.append(key)
                remaining.remove(key)
                progressed = True
        if not progressed:                  # defensive: should never happen (graph is acyclic)
            ordered.extend(remaining)
            break
    return ordered


def ensure_default_catalog() -> int:
    """Create the default courses/lessons if missing.  Idempotent; returns courses created."""
    created = 0
    with session_scope() as s:
        courses, lessons = CourseRepository(s), LessonRepository(s)
        for slug, (title, description, level, keys) in DEFAULT_COURSES.items():
            if courses.get_by_slug(slug):
                continue
            course = courses.add(Course(slug=slug, title=title, description=description, level=level))
            for index, key in enumerate(_ordered_topics(keys), start=1):
                lessons.add(Lesson(
                    course_id=course.id, topic_key=key, title=title_for(key), order_index=index,
                    estimated_minutes=15, difficulty=level,
                ))
            created += 1
    return created


def create_course(owner_id: int, title: str, description: str, topic_keys: list[str], level: str = "Beginner") -> int:
    """Teacher-created course made of existing topic packs.  Returns the course id."""
    title = " ".join(str(title).split())[:120]
    if len(title) < 3:
        raise ValueError("Course title must be at least 3 characters.")
    keys = [topic_key(k) for k in topic_keys if topic_key(k)]
    if not keys:
        raise ValueError("Choose at least one topic for the course.")
    slug = "-".join(title.lower().split())[:70] or "course"
    with session_scope() as s:
        courses, lessons = CourseRepository(s), LessonRepository(s)
        user = UserRepository(s).get(owner_id)
        if user is None or user.role not in ("teacher", "admin"):
            raise PermissionError("Only teachers can create courses.")
        base, n = slug, 1
        while courses.get_by_slug(slug):
            n += 1
            slug = f"{base}-{n}"
        course = courses.add(Course(slug=slug, title=title, description=description[:1000], level=level, owner_id=owner_id))
        for index, key in enumerate(keys, start=1):
            lessons.add(Lesson(course_id=course.id, topic_key=key, title=title_for(key), order_index=index, difficulty=level))
        return course.id


# ── reading ──────────────────────────────────────────────────────────────────
def list_courses(user_id: int | None = None) -> list[CourseView]:
    """Published courses; with ``user_id`` the enrolment flag and progress are filled in."""
    with session_scope() as s:
        enrolled = set(EnrollmentRepository(s).course_ids_for_user(user_id)) if user_id else set()
        views = []
        for course in CourseRepository(s).list_published():
            lessons = LessonRepository(s).list_for_course(course.id)
            done = 0
            if user_id:
                rows = ProgressRepository(s).list_for_lessons(user_id, [lesson.id for lesson in lessons])
                done = sum(1 for r in rows if r.status == "completed")
            views.append(CourseView(
                id=course.id, slug=course.slug, title=course.title, description=course.description,
                level=course.level, lesson_count=len(lessons), enrolled=course.id in enrolled,
                completed_lessons=done, percent=completion_rate(done, len(lessons)),
            ))
        return views


def get_course(course_id: int, user_id: int | None = None) -> CourseView | None:
    """One course with its lessons (and per-lesson progress when ``user_id`` is given)."""
    graph = build_graph()
    with session_scope() as s:
        course = CourseRepository(s).get(course_id)
        if course is None:
            return None
        lessons = LessonRepository(s).list_for_course(course_id)
        progress = {}
        enrolled = False
        if user_id:
            progress = {p.lesson_id: p for p in ProgressRepository(s).list_for_lessons(user_id, [lesson.id for lesson in lessons])}
            enrolled = EnrollmentRepository(s).is_enrolled(user_id, course_id)
        lesson_views = []
        for lesson in lessons:
            row = progress.get(lesson.id)
            prereqs = graph[lesson.topic_key].prerequisites if lesson.topic_key in graph else ()
            lesson_views.append(LessonView(
                id=lesson.id, title=lesson.title, topic_key=lesson.topic_key, order_index=lesson.order_index,
                estimated_minutes=lesson.estimated_minutes, difficulty=lesson.difficulty,
                status=row.status if row else "not_started", percent=row.percent if row else 0.0,
                locked_by=tuple(title_for(p) for p in prereqs),
            ))
        done = sum(1 for lv in lesson_views if lv.status == "completed")
        return CourseView(
            id=course.id, slug=course.slug, title=course.title, description=course.description,
            level=course.level, lesson_count=len(lessons), enrolled=enrolled, completed_lessons=done,
            percent=completion_rate(done, len(lessons)), lessons=lesson_views,
        )


# ── writing ──────────────────────────────────────────────────────────────────
def enroll(user_id: int, course_id: int) -> bool:
    """Enrol a user.  Returns True if newly enrolled, False if they already were."""
    with session_scope() as s:
        if CourseRepository(s).get(course_id) is None:
            raise LookupError("Course not found.")
        _, created = EnrollmentRepository(s).enroll(user_id, course_id)
        return created


def update_lesson_progress(
    user_id: int, lesson_id: int, *, percent: float | None = None, completed: bool = False, seconds: int = 0
) -> None:
    with session_scope() as s:
        if LessonRepository(s).get(lesson_id) is None:
            raise LookupError("Lesson not found.")
        ProgressRepository(s).upsert(
            user_id, lesson_id, status="completed" if completed else None, percent=percent, add_seconds=seconds
        )


def next_lesson(user_id: int, course_id: int) -> LessonView | None:
    """First not-yet-completed lesson of a course (the "Continue" button)."""
    course = get_course(course_id, user_id)
    if course is None:
        return None
    return next((lesson for lesson in course.lessons if lesson.status != "completed"), None)


def enrolled_topic_keys(user_id: int) -> set[str]:
    """Topic keys of every lesson in the courses the student is enrolled in."""
    with session_scope() as s:
        keys: set[str] = set()
        for course_id in EnrollmentRepository(s).course_ids_for_user(user_id):
            keys.update(lesson.topic_key for lesson in LessonRepository(s).list_for_course(course_id))
        return keys


def course_completion_report(course_id: int, actor_id: int) -> list[dict[str, object]]:
    """Teacher view: one row per enrolled student with lessons completed and percent."""
    with session_scope() as s:
        actor = UserRepository(s).get(actor_id)
        course = CourseRepository(s).get(course_id)
        if actor is None or actor.role not in ("teacher", "admin"):
            raise PermissionError("Only teachers or administrators may view class completion.")
        if course is None:
            raise LookupError("Course not found.")
        if actor.role != "admin" and course.owner_id not in (None, actor.id):
            raise PermissionError("You may only view analytics for your own course.")
        lessons = LessonRepository(s).list_for_course(course_id)
        lesson_ids = [lesson.id for lesson in lessons]
        rows = []
        for uid in EnrollmentRepository(s).user_ids_for_course(course_id):
            user = UserRepository(s).get(uid)
            if user is None:
                continue
            done = sum(1 for p in ProgressRepository(s).list_for_lessons(uid, lesson_ids) if p.status == "completed")
            rows.append({
                "student": user.full_name, "username": user.username, "completed": done,
                "total": len(lessons), "percent": completion_rate(done, len(lessons)),
            })
        return sorted(rows, key=lambda r: (-float(r["percent"]), str(r["student"])))
