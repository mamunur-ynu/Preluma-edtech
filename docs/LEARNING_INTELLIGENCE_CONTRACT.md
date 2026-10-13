# Learning intelligence contract (ADR-011 design, not yet migrated)

The existing `QuizAttempt.course_id`/`lesson_id` remains the evidence source. Global `SkillProfile` remains available to Streamlit while course-specific projections are introduced; no old ambiguous attempt is assigned from today's enrollment.

## Append-only event record

Proposed `learning_events` fields: `id` (UUID primary key), `schema_version` (positive integer), `event_type` (`quiz_completed`, `lesson_completed`, `recommendation_dismissed` initially), `user_id`, nullable `course_id` and `lesson_id`, `source_type`, `source_id`, `producer`, `idempotency_key`, `occurred_at` (UTC), `recorded_at` (UTC), and minimal versioned `payload_json`. Unique `(producer, idempotency_key)` prevents retries from double-counting. A quiz event stores score, total, canonical topic, duration and aggregate skill/concept results—not raw answers or document contents. `course_id` can be non-null only when a validated explicit course or immutable lesson proves attribution. The event writer must use the same database transaction as the source attempt and a transactional outbox row; publishing to Redis is optional and must not be the sole durable record.

An event is immutable after commit. Corrections are new compensating events with a reference to the superseded event. User deletion/privacy retention needs a separate reviewed policy before migration. Teacher reads must pass existing course ownership/enrollment checks; there is no general event-feed endpoint in API v1.

## Course-specific projection

Proposed `course_mastery`: unique `(user_id, course_id, topic, concept)`, `score` (0–100), `evidence_count`, `last_event_id`, `last_practiced_at`, `projection_version`, `updated_at`. Only attributed, enrolled-at-event-time evidence for that exact course/topic contributes. Ambiguous or unattributed events update neither course projection nor teacher course charts. Rebuild projections deterministically in `(occurred_at, id)` order, idempotently checkpointing `last_event_id`. Keep existing global mastery separate; never copy it into a course row.

Initial transparent scoring proposal: latest three valid quiz percentages weighted newest-to-oldest `3:2:1`; clamp to 0–100. One result is marked *provisional* and cannot claim mastery. A course topic is *ready for next lesson* only after at least two attributable attempts and a weighted score of at least 80. The exact threshold/weights require teacher review and evaluation before activation; they are not a proven learning-efficacy claim.

## Explainable recommendation rules

Priority is deterministic and auditable. (1) No attributable attempt for the next enrolled lesson → `cold_start`, reason cites the lesson title and absence of evidence. (2) At least two attempts and weighted score below 70 → `practice`, reason includes recent score range, count and course. (3) Last evidence older than 14 days with score below 80 → `review`, reason includes date. (4) Two or more attempts and score at least 80 → `next_lesson`, reason cites the satisfied threshold. Ties use published course order, then lesson order. Every recommendation stores rule ID/version, exact evidence event IDs, score/count and generated time. A teacher can see why a step was proposed; students see a plain-language explanation. An LLM may rewrite tone, never determine ordering or invent evidence.

## Safe migration and verification

1. Add nullable schema and outbox with Alembic; rehearse upgrade/downgrade on synthetic SQLite, then isolated PostgreSQL copy.
2. Dual-write new quiz completion and event in one transaction. Existing Streamlit behavior remains unchanged.
3. Backfill only attempts with verified `course_id` or `lesson_id`; quarantine ambiguous rows. Compare source/event counts and hashes.
4. Build projection as a replayable, idempotent service; test multi-course same-topic isolation, retry, out-of-order delivery, correction, account deletion and authorization.
5. Shadow recommendations against the existing plan before any UI cutover; publish measurement and teacher review. Redis/background workers are introduced only if synchronous outbox draining misses a measured latency/reliability target.
