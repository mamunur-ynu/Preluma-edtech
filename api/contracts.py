"""Explicit, versioned response shapes shared with the future BFF."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StatusResponse(Contract):
    status: str
    api_version: str


class CourseSummary(Contract):
    id: int
    slug: str
    title: str
    description: str
    level: str
    lesson_count: int
    enrolled: bool
    completed_lessons: int
    percent: float


class CourseListResponse(Contract):
    courses: list[CourseSummary]


class CurrentUserResponse(Contract):
    id: int
    username: str
    full_name: str
    role: str


class CourseRecommendationResponse(Contract):
    """Read-only shadow decision; not an activated study-plan workflow."""

    course_id: int
    lesson_id: int | None
    rule_id: str
    rule_version: int
    topic: str | None
    title: str
    reason: str
    score: float | None
    attempts: int
    evidence_event_ids: list[str]


class LoginRequest(Contract):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=512)


class SessionResponse(Contract):
    session_token: str
    expires_in_seconds: int
