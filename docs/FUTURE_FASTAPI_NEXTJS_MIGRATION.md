# Future FastAPI + Next.js Migration Contract

This document is a staged migration plan, not an instruction to replace the working Streamlit application now.

## Goals

- Keep `core/`, `services/`, `database/`, `ai/`, `auth/` and `security/` as the shared implementation.
- Add FastAPI as a transport/auth boundary beside Streamlit.
- Move screens to Next.js incrementally while both clients use the same PostgreSQL database and service contracts.
- Replace the demo-only Streamlit session bridge with secure server-set cookies.

## Authentication contract

- FastAPI resolves an opaque server-side session token to a current active user on every request.
- Browser sessions use `HttpOnly; Secure; SameSite=Lax` (or stricter) cookies with CSRF protection on state changes.
- Native/API clients may use short-lived bearer tokens mapped to the same revocable session store.
- Role is never accepted from a request body or token claim without a current database lookup.
- Login/reset/AI routes have shared-store user and IP rate limits.
- Privilege change, password change, deactivation and reset revoke all existing sessions.

## Proposed HTTP contracts

| Method and path | Service | Authorization |
|---|---|---|
| `POST /v1/auth/login` | `auth.login`, `auth.start_session` | anonymous + rate limit |
| `POST /v1/auth/logout` | `auth.end_session` | current session |
| `GET /v1/me` | resolved `AuthUser` | signed in |
| `GET /v1/me/dashboard` | `learning_service.get_dashboard` | self |
| `GET /v1/me/recommendations` | `recommendation_service.get_plan` | self |
| `GET /v1/courses` | `course_service.list_courses` | signed in |
| `POST /v1/courses/{id}/enrol` | `course_service.enroll` | self/admin |
| `POST /v1/quiz-attempts` | `learning_service.record_quiz_attempt` | self; idempotency key |
| `POST /v1/tutor/ask` | `ai_service.ask_tutor` | self + course visibility + budget |
| `GET /v1/tutor/sessions/{id}` | `ai_service.get_history` | session owner only |
| `DELETE /v1/tutor/sessions/{id}` | `ai_service.clear_session` | session owner only |
| `POST /v1/knowledge-documents` | `ai_service.index_document` | teacher/admin + course ownership |
| `DELETE /v1/knowledge-documents/{id}` | `ai_service.remove_document` | uploader/admin |
| `GET /v1/teacher/courses/{id}/analytics` | `course_service.course_completion_report` | owner/admin |
| `POST /v1/admin/users/{username}/reset-code` | `auth.issue_reset_code` | teacher/admin policy |
| `PATCH /v1/admin/users/{username}` | `user_service.set_active` | admin only |

Every mutation returns an audit correlation ID. Quiz/submission/upload mutations accept an idempotency key and reject cross-user reuse.

## Event/data contracts

- `QuizAttemptRecorded`: attempt ID, user ID, course/lesson/topic, score/total, duration, timestamp; no raw password/session data.
- `MasteryUpdated`: user ID, topic/concept, previous/current mastery, evidence attempt ID.
- `DocumentIndexed`: document ID, owner ID, course ID, visibility, content SHA-256, version, chunk count.
- `AccountStateChanged`: actor ID, target ID, previous/new active state, timestamp.
- `LegacyImportCompleted`: source hashes, inserted/skipped/quarantined counts, operator-approved run ID.

Events should be transactional outbox rows before a real queue is introduced. Analytics labels must be derived from stored events, not fabricated.

## Rollout sequence

1. **Prerequisites:** verified PostgreSQL staging, approved Alembic migration, reconciled legacy import, object-storage policy and external auth threat review.
2. **FastAPI read-only sidecar:** health, current user, courses, dashboards and tutor history.
3. **Secure auth transport:** gateway/cookies, CSRF, shared rate limits, session rotation and audit log.
4. **Write APIs:** quiz attempts, recommendations, documents, homework and projects with idempotency/authorization tests.
5. **Next.js student shell:** login, dashboard and courses; Streamlit remains available.
6. **Tutor and Mission:** citations/streaming, then the five-step Mission screen-by-screen.
7. **Teacher/admin:** analytics, knowledge base, assignments, projects and account controls.
8. **Cutover:** canary users, telemetry, rollback switch, then retire only the replaced Streamlit route—not the back-end layer.

## Non-goals for the current release

- No React/Next.js rewrite
- No FastAPI package added solely as a placeholder
- No JWT role claims trusted without server state
- No public upload bucket
- No production deployment or GitHub push
