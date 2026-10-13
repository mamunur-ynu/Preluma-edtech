"""Read-only FastAPI adapter; Streamlit remains the functional application.

This service is for a private BFF-to-backend network only. The shared key is a
server-to-server admission control, *not* a replacement for TLS, network isolation
or a browser cookie implementation. No browser should receive either header.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response

from api.contracts import (
    CourseListResponse, CourseRecommendationResponse, CourseSummary, CurrentUserResponse,
    LoginRequest, SessionResponse, StatusResponse,
)
from auth.authentication import login
from auth.sessions import (
    replace_session_token, resolve_session_token, revoke_session_token, rotate_session_token,
)
from config import get_setting, get_settings
from database.connection import session_scope
from database.repository import UserRepository
from services.course_service import list_courses
from services.course_recommendations import get_course_recommendation

app = FastAPI(title="Preluma internal API", version="0.1.0", docs_url=None,
              redoc_url=None, openapi_url=None)


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def require_bff(x_preluma_bff_key: Annotated[str | None, Header()] = None) -> None:
    expected = get_setting("PRELUMA_BFF_SHARED_KEY")
    if len(expected) < 32:
        raise HTTPException(503, "Internal API is not configured.")
    if not x_preluma_bff_key or not secrets.compare_digest(x_preluma_bff_key, expected):
        raise HTTPException(401, "BFF authentication required.")


def require_user(
    _: Annotated[None, Depends(require_bff)],
    x_preluma_session: Annotated[str | None, Header()] = None,
) -> int:
    user_id = resolve_session_token(x_preluma_session or "")
    if user_id is None:
        raise HTTPException(401, "Active session required.")
    return user_id


def _courses(user_id: int | None = None) -> CourseListResponse:
    try:
        rows = list_courses(user_id)
    except PermissionError as exc:
        raise HTTPException(403, "Account access denied.") from exc
    return CourseListResponse(courses=[CourseSummary(
        id=row.id, slug=row.slug, title=row.title, description=row.description,
        level=row.level, lesson_count=row.lesson_count, enrolled=row.enrolled,
        completed_lessons=row.completed_lessons, percent=row.percent,
    ) for row in rows])


@app.get("/v1/status", response_model=StatusResponse, dependencies=[Depends(require_bff)])
def status() -> StatusResponse:
    return StatusResponse(status="ok", api_version="v1")


@app.get("/v1/catalog/courses", response_model=CourseListResponse,
         dependencies=[Depends(require_bff)])
def catalog_courses() -> CourseListResponse:
    return _courses()


@app.get("/v1/me", response_model=CurrentUserResponse)
def current_user(user_id: Annotated[int, Depends(require_user)]) -> CurrentUserResponse:
    with session_scope() as session:
        user = UserRepository(session).get(user_id)
        if user is None or not user.is_active:
            raise HTTPException(401, "Active session required.")
        return CurrentUserResponse(id=user.id, username=user.username,
                                   full_name=user.full_name, role=user.role)


@app.get("/v1/me/courses", response_model=CourseListResponse)
def my_courses(user_id: Annotated[int, Depends(require_user)]) -> CourseListResponse:
    return _courses(user_id)


@app.get("/v1/me/courses/{course_id}/recommendation", response_model=CourseRecommendationResponse)
def my_course_recommendation(
    course_id: int, user_id: Annotated[int, Depends(require_user)],
) -> CourseRecommendationResponse:
    """Expose only this session's enrolled-course shadow recommendation."""
    try:
        result = get_course_recommendation(user_id, course_id)
    except PermissionError as exc:
        raise HTTPException(403, "Course access denied.") from exc
    return CourseRecommendationResponse(
        course_id=result.course_id, lesson_id=result.lesson_id,
        rule_id=result.rule_id, rule_version=result.rule_version,
        topic=result.topic, title=result.title, reason=result.reason,
        score=result.score, attempts=result.attempts,
        evidence_event_ids=list(result.evidence_event_ids),
    )


@app.post("/v1/auth/login", response_model=SessionResponse, dependencies=[Depends(require_bff)])
def login_session(
    payload: LoginRequest, x_preluma_session: Annotated[str | None, Header()] = None,
) -> SessionResponse:
    """Private BFF-only credential exchange; never call this from browser JavaScript."""
    user, _ = login(payload.username, payload.password)
    if user is None:
        raise HTTPException(401, "Invalid credentials.")
    return SessionResponse(
        session_token=replace_session_token(user.id, x_preluma_session),
        expires_in_seconds=get_settings().session_ttl_seconds,
    )


@app.post("/v1/auth/rotate", response_model=SessionResponse, dependencies=[Depends(require_bff)])
def rotate_session(x_preluma_session: Annotated[str | None, Header()] = None) -> SessionResponse:
    replacement = rotate_session_token(x_preluma_session or "")
    if replacement is None:
        raise HTTPException(401, "Active session required.")
    return SessionResponse(
        session_token=replacement,
        expires_in_seconds=get_settings().session_ttl_seconds,
    )


@app.post("/v1/auth/logout", status_code=204, dependencies=[Depends(require_bff)])
def logout_session(x_preluma_session: Annotated[str | None, Header()] = None) -> Response:
    revoke_session_token(x_preluma_session or "")
    return Response(status_code=204)
