# Learning intelligence contract (ADR-011 incremental implementation)

The existing `QuizAttempt.course_id`/`lesson_id` remains the evidence source. Global `SkillProfile` remains available to Streamlit while course-specific projections are introduced; no old ambiguous attempt is assigned from today's enrollment.

## Append-only event record

Revision `20261013_06` adds `learning_events`, `learning_outbox` and `course_mastery`. The implemented `quiz.completed` event stores a UUID, schema version, user/course/lesson provenance, source attempt, producer/idempotency key, UTC timestamps, and only canonical topic, score, total and percentage in JSON. It never stores questions, answers or document text. Unique `(producer, idempotency_key)` prevents duplicate evidence. `record_quiz_attempt` appends the event and outbox marker in the source attempt's transaction. Ambiguous attempts have `course_id = NULL` and do not project to any course. No Redis publisher or event-feed API is enabled.

The service has no event update path, but database-level append-only permissions/triggers, compensating corrections, retention/account-deletion policy and outbox delivery are not implemented. Teacher reads must pass existing course ownership/enrollment checks; there is no general event-feed endpoint in API v1.

## Course-specific projection

The implemented topic-level projection has unique `(user_id, course_id, topic, concept)`, mastery (0–100), attempt count, last event/time and projection version. `concept` is currently empty; concept-level evidence is not yet projected. Only quiz events with validated course provenance at recording time are used. The replay orders by `(occurred_at, id)` and replaces only one user's one course's projection, so retries and late evidence yield the same values. Historical enrollment-at-event-time proof is not stored; do not backfill old ambiguous records or claim historical course accuracy. Existing global mastery remains separate.

Implemented score: latest three valid quiz percentages weighted oldest-to-newest `1:2:3` (equivalent to newest-to-oldest `3:2:1`), rounded to one decimal. `attempts` enables callers to treat one result as provisional, but no readiness UI or recommendation activation uses this projection yet. The proposed two-attempt/80 threshold requires teacher review and evaluation; it is not a proven learning-efficacy claim.

## Explainable recommendation rules

Priority is deterministic and auditable. (1) No attributable attempt for the next enrolled lesson → `cold_start`, reason cites the lesson title and absence of evidence. (2) At least two attempts and weighted score below 70 → `practice`, reason includes recent score range, count and course. (3) Last evidence older than 14 days with score below 80 → `review`, reason includes date. (4) Two or more attempts and score at least 80 → `next_lesson`, reason cites the satisfied threshold. Ties use published course order, then lesson order. Every recommendation stores rule ID/version, exact evidence event IDs, score/count and generated time. A teacher can see why a step was proposed; students see a plain-language explanation. An LLM may rewrite tone, never determine ordering or invent evidence.

## Safe migration and verification

1. Add nullable schema and outbox with Alembic; rehearse upgrade/downgrade on synthetic SQLite, then isolated PostgreSQL copy.
2. Dual-write new quiz completion and event in one transaction. Existing Streamlit behavior remains unchanged.
3. Backfill only attempts with verified `course_id` or `lesson_id`; quarantine ambiguous rows. Compare source/event counts and hashes.
4. Build projection as a replayable, idempotent service; test multi-course same-topic isolation, retry, out-of-order delivery, correction, account deletion and authorization.
5. Shadow recommendations against the existing plan before any UI cutover; publish measurement and teacher review. Redis/background workers are introduced only if synchronous outbox draining misses a measured latency/reliability target.
