"""
database/repository.py — the repository pattern.

Each repository wraps **one aggregate** and exposes intention-revealing methods; no SQL or
ORM query leaks into services.  Repositories never commit — the caller's ``session_scope()``
owns the transaction, so a service can combine several repositories atomically.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from database.models import (
    Achievement,
    AIConversationMessage,
    Course,
    Enrollment,
    KnowledgeDocument,
    Lesson,
    PasswordResetToken,
    Progress,
    QuizAttempt,
    QuizMistake,
    Recommendation,
    SkillProfile,
    User,
    UserSession,
    utcnow,
)


class _Repo:
    def __init__(self, session: Session) -> None:
        self.session = session


# ─────────────────────────────────────────────────────────────────────────────
class UserRepository(_Repo):
    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username.strip().lower()))

    def list_by_role(self, role: str | None = None) -> Sequence[User]:
        stmt = select(User).order_by(User.id)
        if role:
            stmt = stmt.where(User.role == role)
        return self.session.scalars(stmt).all()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(User)) or 0

    def set_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self.session.flush()

    def touch_login(self, user: User) -> None:
        user.last_login_at = utcnow()
        self.session.flush()

    def set_learning_style(self, user: User, style: str | None) -> None:
        user.preferred_learning_style = style
        self.session.flush()

    # password-reset tokens ---------------------------------------------------
    def add_reset_token(self, token: PasswordResetToken) -> None:
        self.session.add(token)
        self.session.flush()

    def valid_reset_tokens(self, user_id: int) -> Sequence[PasswordResetToken]:
        return self.session.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > utcnow(),
            )
        ).all()

    def invalidate_reset_tokens(self, user_id: int) -> int:
        result = self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=utcnow())
        )
        return int(result.rowcount or 0)


class SessionRepository(_Repo):
    def add(self, row: UserSession) -> UserSession:
        self.session.add(row)
        self.session.flush()
        return row

    def get_active(self, token_hash: str) -> UserSession | None:
        return self.session.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > utcnow(),
            )
        )

    def revoke(self, token_hash: str) -> None:
        self.session.execute(
            update(UserSession)
            .where(UserSession.token_hash == token_hash, UserSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def revoke_all_for_user(self, user_id: int) -> None:
        self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def purge_expired(self) -> int:
        return self.session.execute(
            delete(UserSession).where(UserSession.expires_at < utcnow())
        ).rowcount or 0


# ─────────────────────────────────────────────────────────────────────────────
class CourseRepository(_Repo):
    def add(self, course: Course) -> Course:
        self.session.add(course)
        self.session.flush()
        return course

    def get(self, course_id: int) -> Course | None:
        return self.session.get(Course, course_id)

    def get_by_slug(self, slug: str) -> Course | None:
        return self.session.scalar(select(Course).where(Course.slug == slug))

    def list_published(self) -> Sequence[Course]:
        return self.session.scalars(
            select(Course).where(Course.is_published.is_(True)).order_by(Course.title)
        ).all()

    def list_owned(self, owner_id: int) -> Sequence[Course]:
        return self.session.scalars(select(Course).where(Course.owner_id == owner_id).order_by(Course.id)).all()


class LessonRepository(_Repo):
    def add(self, lesson: Lesson) -> Lesson:
        self.session.add(lesson)
        self.session.flush()
        return lesson

    def get(self, lesson_id: int) -> Lesson | None:
        return self.session.get(Lesson, lesson_id)

    def list_for_course(self, course_id: int) -> Sequence[Lesson]:
        return self.session.scalars(
            select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order_index)
        ).all()

    def find_by_topic(self, topic_key: str) -> Sequence[Lesson]:
        return self.session.scalars(select(Lesson).where(Lesson.topic_key == topic_key)).all()

    def count_for_course(self, course_id: int) -> int:
        return self.session.scalar(
            select(func.count()).select_from(Lesson).where(Lesson.course_id == course_id)
        ) or 0


class EnrollmentRepository(_Repo):
    def enroll(self, user_id: int, course_id: int) -> tuple[Enrollment, bool]:
        """Idempotent.  Returns ``(enrollment, created)``."""
        existing = self.session.scalar(
            select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )
        if existing:
            return existing, False
        row = Enrollment(user_id=user_id, course_id=course_id)
        self.session.add(row)
        self.session.flush()
        return row, True

    def course_ids_for_user(self, user_id: int) -> list[int]:
        return list(
            self.session.scalars(select(Enrollment.course_id).where(Enrollment.user_id == user_id))
        )

    def user_ids_for_course(self, course_id: int) -> list[int]:
        return list(
            self.session.scalars(select(Enrollment.user_id).where(Enrollment.course_id == course_id))
        )

    def is_enrolled(self, user_id: int, course_id: int) -> bool:
        return course_id in self.course_ids_for_user(user_id)


class ProgressRepository(_Repo):
    def get(self, user_id: int, lesson_id: int) -> Progress | None:
        return self.session.scalar(
            select(Progress).where(Progress.user_id == user_id, Progress.lesson_id == lesson_id)
        )

    def upsert(
        self,
        user_id: int,
        lesson_id: int,
        *,
        status: str | None = None,
        percent: float | None = None,
        add_seconds: int = 0,
    ) -> Progress:
        row = self.get(user_id, lesson_id)
        now = utcnow()
        if row is None:
            row = Progress(user_id=user_id, lesson_id=lesson_id, started_at=now)
            self.session.add(row)
        if percent is not None:
            row.percent = max(row.percent or 0.0, min(100.0, float(percent)))
        if status is not None:
            row.status = status
        elif row.status == "not_started":
            row.status = "in_progress"
        if row.status == "completed":
            row.percent = 100.0
            row.completed_at = row.completed_at or now
        row.time_spent_seconds = (row.time_spent_seconds or 0) + max(0, int(add_seconds))
        row.updated_at = now
        self.session.flush()
        return row

    def list_for_user(self, user_id: int) -> Sequence[Progress]:
        return self.session.scalars(select(Progress).where(Progress.user_id == user_id)).all()

    def list_for_lessons(self, user_id: int, lesson_ids: Iterable[int]) -> Sequence[Progress]:
        ids = list(lesson_ids)
        if not ids:
            return []
        return self.session.scalars(
            select(Progress).where(Progress.user_id == user_id, Progress.lesson_id.in_(ids))
        ).all()

    def completed_dates(self, user_id: int) -> list[date]:
        rows = self.session.scalars(
            select(Progress.updated_at).where(Progress.user_id == user_id)
        ).all()
        return [r.date() for r in rows if r]


class QuizAttemptRepository(_Repo):
    def add(self, attempt: QuizAttempt, mistakes: Iterable[QuizMistake] = ()) -> QuizAttempt:
        self.session.add(attempt)
        self.session.flush()
        for mistake in mistakes:
            mistake.attempt_id = attempt.id
            mistake.user_id = attempt.user_id
            mistake.topic = mistake.topic or attempt.topic
            self.session.add(mistake)
        self.session.flush()
        return attempt

    def list_for_user(
        self, user_id: int, *, limit: int | None = None, topic: str | None = None
    ) -> Sequence[QuizAttempt]:
        stmt = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        if topic:
            stmt = stmt.where(QuizAttempt.topic == topic)
        stmt = stmt.order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
        if limit:
            stmt = stmt.limit(limit)
        return self.session.scalars(stmt).all()

    def count_for_user(self, user_id: int) -> int:
        return self.session.scalar(
            select(func.count()).select_from(QuizAttempt).where(QuizAttempt.user_id == user_id)
        ) or 0

    def activity_dates(self, user_id: int) -> list[date]:
        rows = self.session.scalars(
            select(QuizAttempt.created_at).where(QuizAttempt.user_id == user_id)
        ).all()
        return [r.date() for r in rows]

    def mistakes_for_user(self, user_id: int, limit: int = 50) -> Sequence[QuizMistake]:
        return self.session.scalars(
            select(QuizMistake)
            .where(QuizMistake.user_id == user_id)
            .order_by(QuizMistake.id.desc())
            .limit(limit)
        ).all()

    def all_recent(self, days: int = 90, course_ids: set[int] | None = None) -> Sequence[QuizAttempt]:
        since = utcnow() - timedelta(days=days)
        stmt = select(QuizAttempt).where(QuizAttempt.created_at >= since)
        if course_ids is not None:
            if not course_ids:
                return []
            stmt = stmt.where(QuizAttempt.course_id.in_(course_ids))
        return self.session.scalars(stmt.order_by(QuizAttempt.created_at)).all()

    def mistake_counts_by_concept(
        self, user_ids: set[int], course_ids: set[int] | None = None,
        excluded_attempt_ids: set[int] | None = None,
    ) -> list[tuple[str, str, int]]:
        if not user_ids:
            return []
        stmt = (
            select(QuizMistake.topic, QuizMistake.concept, func.count())
            .join(QuizAttempt, QuizMistake.attempt_id == QuizAttempt.id)
            .where(QuizMistake.user_id.in_(user_ids))
            .group_by(QuizMistake.topic, QuizMistake.concept)
            .order_by(func.count().desc())
        )
        if course_ids is not None:
            if not course_ids:
                return []
            stmt = stmt.where(QuizAttempt.course_id.in_(course_ids))
        if excluded_attempt_ids:
            stmt = stmt.where(QuizAttempt.id.not_in(excluded_attempt_ids))
        rows = self.session.execute(stmt).all()
        return [(t, c, int(n)) for t, c, n in rows]


class SkillProfileRepository(_Repo):
    def get(self, user_id: int, topic: str, concept: str = "") -> SkillProfile | None:
        return self.session.scalar(
            select(SkillProfile).where(
                SkillProfile.user_id == user_id,
                SkillProfile.topic == topic,
                SkillProfile.concept == concept,
            )
        )

    def get_or_create(self, user_id: int, topic: str, concept: str = "") -> SkillProfile:
        row = self.get(user_id, topic, concept)
        if row is None:
            row = SkillProfile(user_id=user_id, topic=topic, concept=concept)
            self.session.add(row)
            self.session.flush()
        return row

    def list_for_user(self, user_id: int, *, topics_only: bool = False) -> Sequence[SkillProfile]:
        stmt = select(SkillProfile).where(SkillProfile.user_id == user_id)
        if topics_only:
            stmt = stmt.where(SkillProfile.concept == "")
        return self.session.scalars(stmt.order_by(SkillProfile.topic, SkillProfile.concept)).all()

    def list_topic_level(self) -> Sequence[SkillProfile]:
        """Topic-level rows of every student (class analytics)."""
        return self.session.scalars(select(SkillProfile).where(SkillProfile.concept == "")).all()


class ConversationRepository(_Repo):
    def add(self, message: AIConversationMessage) -> AIConversationMessage:
        self.session.add(message)
        self.session.flush()
        return message

    def history(self, user_id: int, session_id: str, limit: int = 20) -> list[AIConversationMessage]:
        rows = self.session.scalars(
            select(AIConversationMessage)
            .where(
                AIConversationMessage.user_id == user_id,
                AIConversationMessage.session_id == session_id,
            )
            .order_by(AIConversationMessage.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def recent_user_messages(self, user_id: int, limit: int = 200) -> Sequence[AIConversationMessage]:
        return self.session.scalars(
            select(AIConversationMessage)
            .where(AIConversationMessage.user_id == user_id, AIConversationMessage.role == "user")
            .order_by(AIConversationMessage.id.desc())
            .limit(limit)
        ).all()

    def delete_session(self, user_id: int, session_id: str) -> int:
        result = self.session.execute(
            delete(AIConversationMessage).where(
                AIConversationMessage.user_id == user_id,
                AIConversationMessage.session_id == session_id,
            )
        )
        return result.rowcount or 0

    def activity_dates(self, user_id: int) -> list[date]:
        rows = self.session.scalars(
            select(AIConversationMessage.created_at).where(AIConversationMessage.user_id == user_id)
        ).all()
        return [r.date() for r in rows]

    def purge_older_than(self, user_id: int, cutoff) -> int:
        result = self.session.execute(
            delete(AIConversationMessage).where(
                AIConversationMessage.user_id == user_id,
                AIConversationMessage.created_at < cutoff,
            )
        )
        return int(result.rowcount or 0)


class RecommendationRepository(_Repo):
    def replace_active(self, user_id: int, items: Iterable[Recommendation]) -> list[Recommendation]:
        """Supersede the user's active recommendations with a fresh set."""
        self.session.execute(
            update(Recommendation)
            .where(Recommendation.user_id == user_id, Recommendation.status == "active")
            .values(status="superseded")
        )
        created = []
        for item in items:
            item.user_id = user_id
            self.session.add(item)
            created.append(item)
        self.session.flush()
        return created

    def active_for_user(self, user_id: int) -> Sequence[Recommendation]:
        return self.session.scalars(
            select(Recommendation)
            .where(Recommendation.user_id == user_id, Recommendation.status == "active")
            .order_by(Recommendation.priority)
        ).all()

    def set_status(self, rec_id: int, user_id: int, status: str) -> bool:
        result = self.session.execute(
            update(Recommendation)
            .where(Recommendation.id == rec_id, Recommendation.user_id == user_id)
            .values(status=status)
        )
        return bool(result.rowcount)


class AchievementRepository(_Repo):
    def award(self, user_id: int, code: str, title: str, description: str = "") -> bool:
        """Return True if newly awarded, False if the user already had it."""
        exists = self.session.scalar(
            select(Achievement).where(Achievement.user_id == user_id, Achievement.code == code)
        )
        if exists:
            return False
        self.session.add(Achievement(user_id=user_id, code=code, title=title, description=description))
        self.session.flush()
        return True

    def list_for_user(self, user_id: int) -> Sequence[Achievement]:
        return self.session.scalars(
            select(Achievement).where(Achievement.user_id == user_id).order_by(Achievement.earned_at)
        ).all()

    def codes_for_user(self, user_id: int) -> set[str]:
        return {a.code for a in self.list_for_user(user_id)}


class KnowledgeDocumentRepository(_Repo):
    def add(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self.session.add(doc)
        self.session.flush()
        return doc

    def list_all(self) -> Sequence[KnowledgeDocument]:
        return self.session.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())).all()

    def get(self, doc_id: int) -> KnowledgeDocument | None:
        return self.session.get(KnowledgeDocument, doc_id)

    def get_by_digest(
        self, digest: str, course_id: int | None, uploaded_by: int, visibility: str
    ) -> KnowledgeDocument | None:
        return self.session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.content_sha256 == digest,
                KnowledgeDocument.course_id == course_id,
                KnowledgeDocument.uploaded_by == uploaded_by,
                KnowledgeDocument.visibility == visibility,
            )
        )

    def list_for_actor(
        self,
        actor_id: int,
        *,
        is_staff: bool,
        course_ids: Iterable[int] = (),
    ) -> Sequence[KnowledgeDocument]:
        allowed_courses = tuple(course_ids)
        conditions = [KnowledgeDocument.visibility == "public", KnowledgeDocument.uploaded_by == actor_id]
        if allowed_courses:
            conditions.append(KnowledgeDocument.course_id.in_(allowed_courses))
        if is_staff:
            conditions.append(KnowledgeDocument.visibility == "staff")
        from sqlalchemy import or_

        return self.session.scalars(
            select(KnowledgeDocument).where(or_(*conditions)).order_by(KnowledgeDocument.id.desc())
        ).all()

    def delete(self, doc_id: int) -> bool:
        return bool(self.session.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)).rowcount)
