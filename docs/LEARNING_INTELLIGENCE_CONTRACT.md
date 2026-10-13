# Learning intelligence contract (ADR-011 incremental implementation)

The existing `QuizAttempt.course_id`/`lesson_id` remains the evidence source. Global `SkillProfile` remains available to Streamlit while course-specific projections are introduced; no old ambiguous attempt is assigned from today's enrollment.

## Append-only event record

Revision `20261013_06` adds `learning_events`, `learning_outbox` and `course_mastery`. The implemented `quiz.completed` event stores a UUID, schema version, user/course/lesson provenance, source attempt, producer/idempotency key, UTC timestamps, and only canonical topic, score, total, percentage and per-concept aggregate counts in JSON. It never stores questions, answers or document text. Concept labels over 80 characters are omitted rather than silently merged. Unique `(producer, idempotency_key)` prevents duplicate evidence. `record_quiz_attempt` appends the event and outbox marker in the source attempt's transaction. Ambiguous attempts have `course_id = NULL` and do not project to any course. No Redis publisher or event-feed API is enabled.

The service has no event update path, but database-level append-only permissions/triggers, compensating corrections and retention/account-deletion policy are not implemented. An opt-in local outbox replay function now acknowledges one event and rebuilds its attributed course projection in one transaction; it is not scheduled, has no external publisher and is not production-ready. Teacher reads must pass existing course ownership/enrollment checks; there is no general event-feed endpoint in API v1. The sole learning endpoint is `GET /v1/me/courses/{course_id}/recommendation`: a BFF-key and revocable-session protected, enrolled-course-only read of the shadow rule result. It does not expose raw quiz text, answers, other users' records or any learning mutation, and is not wired into either UI.

## Course-specific projection

The implemented topic- and concept-level projection has unique `(user_id, course_id, topic, concept)`, mastery (0–100), attempt count, last event/time and projection version. The empty concept is the topic aggregate; non-empty concepts use aggregate correct/total counts from attributable question results. Only quiz events with validated course provenance at recording time are used. The replay orders by `(occurred_at, id)` and replaces only one user's one course's projection, so retries and late evidence yield the same values. Older events without concept aggregates still replay at topic level. Historical enrollment-at-event-time proof is not stored; do not backfill old ambiguous records or claim historical course accuracy. Existing global mastery remains separate.

Implemented score: latest three valid quiz percentages weighted oldest-to-newest `1:2:3` (equivalent to newest-to-oldest `3:2:1`), rounded to one decimal. `attempts` enables callers to treat one result as provisional, but no readiness UI or recommendation activation uses this projection yet. The proposed two-attempt/80 threshold requires teacher review and evaluation; it is not a proven learning-efficacy claim.

## Explainable recommendation rules

`services/course_recommendations.py` implements a read-only shadow decision for one actively enrolled student's course. It walks lessons in stable order. Missing attributable evidence yields `cold_start`; one attempt yields `provisional_practice`; two or more below 70 yield `practice`; a 70–79 score older than 14 days yields `review`; a fresh 70–79 score yields `practice`; two or more at 80+ advance to the next lesson, or `course_ready` when all lessons qualify. Each result includes rule ID/version, score/count, evidence event IDs and a plain-language reason. The old global student plan and Streamlit UI are unchanged. This is a testable policy proposal, not an activated personalized learning claim; teacher review and shadow evaluation are required before cutover. No LLM decides the ordering.

## Safe migration and verification

1. Add nullable schema and outbox with Alembic; rehearse upgrade/downgrade on synthetic SQLite, then isolated PostgreSQL copy.
2. Dual-write new quiz completion and event in one transaction. Existing Streamlit behavior remains unchanged.
3. Backfill only attempts with verified `course_id` or `lesson_id`; quarantine ambiguous rows. Compare source/event counts and hashes.
4. Build projection as a replayable, idempotent service; test multi-course same-topic isolation, retry, out-of-order delivery, correction, account deletion and authorization.
5. Shadow recommendations against the existing plan before any UI cutover; publish measurement and teacher review. Redis/background workers are introduced only if synchronous outbox draining misses a measured latency/reliability target.
