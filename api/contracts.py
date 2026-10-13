"""Explicit, versioned response shapes shared with the future BFF."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
