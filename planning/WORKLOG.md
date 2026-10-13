# Worklog

## 2026-10-13, 02:11 Asia/Shanghai — baseline and checkout

- Confirmed draft PR #2 on `feature/preluma-release-hardening` at `b13108a1c1f705ef98d64e755eddec0ca4decfc3`; prior GitHub CI runs were successful.
- Created persistent checkout `/Users/mim/Desktop/Preluma/Preluma-edtech-vNEXT-git` without replacing old local packages or Git history.
- The owner-provided Autopilot prompt was initially absent, then arrived at `/Users/mim/Downloads/Preluma_AUTOPILOT_One_Time_Master_Prompt.md`; read all 228 lines and replaced provisional planning with this repository system.

## 2026-10-13, 02:14 Asia/Shanghai — SEC-01

- Curated topic documents now declare public visibility. Old curated entries with missing visibility are reindexed; unlabelled uploaded chunks fail closed.
- Document indexing requires an active teacher/admin uploader before file parsing. Digest reuse is scoped to uploader, course and visibility.
- Negative tests cover unlabelled chunks, missing uploader and duplicate bytes across owners/privacy levels.
- Executed `pytest -q tests/test_security_hardening.py tests/test_ai.py`: 27 passed. Full `pytest -q`: 116 passed in 4.80 s. Ruff, compileall, Bandit and pip-audit passed. Campus/tower hashes match. Commit `1554f3d` pushed to draft PR #2; PR CI status after this commit must be checked separately.

## 2026-10-13, next task — SEC-02

- Found that ordinary login kept only `st.session_state` identity and did not create a server session token unless demo-only “Keep me logged in” was selected. Open tabs were not revalidated after account deactivation or role changes. Implementing server-session validation on each rerun, then testing live revocation and role refresh.

## 2026-10-13, 02:18 Asia/Shanghai — SEC-02 verified

- Every login now starts a revocable server session; each Streamlit rerun resolves the token and refreshes the user's active status, role and name. Browser persistence remains opt-in demo-only. Deactivation, password change and logout revoke open-tab access on the next rerun.
- AI, courses, learning and recommendations reject disabled accounts on the affected private paths. Lesson progress requires enrolment; reset/admin actors must be active.
- Executed focused auth/AppTest/security/database/recommendation suite: 55 passed in 5.10 s after a regression test was corrected to use a real second account. Final full suite: 123 passed in 5.60 s; 10 AppTests in 4.23 s; Ruff, compileall, Bandit, pip-audit all PASS; both image hashes unchanged.
- A real login form was also exercised through AppTest: it created a server token, and logout revoked it. External HttpOnly gateway and production identity transport remain open gates.

## 2026-10-13, 06:46 Asia/Shanghai — SEC-04

- Class overview and student drill-down now require an active teacher/admin actor. Published course access is limited to owned/shared courses for teachers, while administrators can see all. Teacher UI course selectors use the same scoped list.
- Global teacher roster, individual course roster, mistakes and completion aggregates are limited to accessible enrollments. Negative tests cover student/inactive actor, cross-owner course and student access, and other-class mistake leakage.
- Executed focused tests: 13 passed in 4.68 s. Full suite: 126 passed in 5.03 s. Ruff passed; remaining gates are recorded in the milestone report after they finish.
- Limitation: attempts/mastery lack course provenance, so course-specific metrics for a student enrolled in multiple courses may include their other learning activity. DATA-03 records the schema work needed; this milestone claims roster privacy, not precise course-specific activity.

## 2026-10-13, 06:50 Asia/Shanghai — DATA-02

- Startup now reconciles uploaded document metadata with persisted vector IDs, counts and privacy attributes. Orphan/tampered vectors are removed; missing vectors leave database rows with zero chunks so owners can re-upload. A saved index whose DB chunk count was not yet committed is repaired.
- Delete now removes searchable vectors before committing database deletion, so an index failure retains metadata for retry. Tests simulate interrupted deletion, missing vectors, tampered visibility/owner, incomplete count commit and failed index deletion.
- Executed 33 focused AI/security/recovery tests in 1.24 s before the final delete-order test; final full suite 130 passed in 5.13 s. Ruff, compileall, Bandit and pip-audit all PASS.
- This is local startup recovery, not multi-worker synchronization. Raw source text is not retained after upload; missing chunks require re-upload. DATA-04 records the distributed index gap.

## 2026-10-13, 06:55 Asia/Shanghai — REL-01

- Built a Git-archive ZIP from the tested PR branch, verified archive CRC, extracted it into an isolated temporary directory and reran the full suite: 130 passed in 6.87 s. Ruff passed and both original image SHA-256 hashes matched. The deliverable and checksum are stored outside the repository in `/Users/mim/Desktop/Preluma/Deliverables/`.
- Draft PR #2 remained unmerged. GitHub checks for the latest push were pending at the time of this checkpoint; they must be read after completion rather than assumed successful.

## 2026-10-13, 15:09 Asia/Shanghai — SEC-03 local hardening (partial)

- Added an in-process reset-code issuance cap per actor/target that leaves the most recent valid code untouched when blocked. Chat and tutor now draw from one per-user local AI request quota.
- Added regression tests for both bypasses and wrote a production shared-limiter/provider-budget contract. Focused auth/security suite: 30 passed in 1.34 s. Full suite: 132 passed in 5.84 s. Ruff, compileall, Bandit and pip-audit passed; both preserved image hashes matched.
- Distributed enforcement and paid-provider budget limits were not implemented or tested; SEC-03 remains in progress. No staging environment, paid provider or production account was touched.
- GitHub feature-branch commit `8ccf25b` was pushed to existing draft PR #2. A ZIP of that commit passed extraction tests: 132 passed in 5.90 s, Ruff passed, both image hashes matched, archive checksum verified. Rebuild after this documentation-only checkpoint commit so filename and HEAD align.

## 2026-10-13, 15:23 Asia/Shanghai — DATA-03

- Added nullable quiz `course_id` plus Alembic revision `20261013_02`. Future attempts carry explicit/uniquely inferred course and lesson IDs. Ambiguous attempts remain unattributed and cannot complete multiple courses' lessons.
- Course-launched Mission preserves the selected course/topic context. Teacher analytics use authorized attributed attempts and mistake joins; per-course drill-down and charts now state quiz averages instead of pretending they are global mastery.
- Synthetic upgrade/downgrade preserved unknown historical rows as NULL and backfilled only rows with explicit lesson IDs. Focused migration/analytics/AppTests passed; final full suite 135 passed in 6.43 s. Ruff, compileall, Bandit and pip-audit passed.
- No real PostgreSQL, staging, production or student data was modified. Historical rows with no course/lesson evidence require a reviewed copied-data reconciliation (DATA-05).

## 2026-10-13, 15:31 Asia/Shanghai — DATA-02 encrypted recovery extension

- Added encrypted extracted-source retention, nullable schema revision `20261013_03`, strict PostgreSQL key requirement and private SQLite demo key. Local startup now rebuilds missing/tampered upload chunks from authenticated ciphertext. Wrong key and old null-ciphertext rows fail closed.
- Added synthetic migration upgrade/downgrade, restart-recovery and key-permission tests. Focused source/migration suite: 7 passed. Full suite: 139 passed in 6.70 s; Ruff, compileall, Bandit and pip-audit passed; both original image hashes matched.
- Private vector-index storage, multi-worker consistency, secret-manager backup/rotation and real PostgreSQL staging remain open. No live database, paid provider or deployment was touched.

## 2026-10-13, 15:46 Asia/Shanghai — SEC-03 shared-counter implementation

- Added `rate_limit_buckets` and Alembic revision `20261013_04`. One atomic UPSERT/RETURNING check shares a fixed-window quota across independent database workers and retains denied attempts. Old buckets are pruned. PostgreSQL refuses process-local fallback.
- Login/reset/AI counters use the shared backend when configured; each provider HTTP attempt consumes a global hourly quota. Without an explicit PostgreSQL provider-call ceiling, live calls fail closed. Synthetic concurrent workers, auth/reset/AI and provider-call tests passed. Full suite: 146 passed in 6.71 s; Ruff, compileall, Bandit and pip-audit passed; both image hashes matched.
- Remaining SEC-03 work: real PostgreSQL multi-worker/outage test, trusted gateway IP quota, provider/model token-price-aware monetary cap and owner alerting. No real provider call or staging deployment was performed.

## 2026-10-13, 16:10 Asia/Shanghai — DATA-04 shared index implementation (partial)

- Added Alembic revision `20261013_05` and a relational vector store. PostgreSQL workers automatically select it; local SQLite demos retain their JSON index unless configured otherwise. Retrieval reads committed database rows each time, and a replacement is one transaction with a PostgreSQL document advisory lock.
- Uploaded chunk text is encrypted before storage in the shared index; public curated text stays readable. Two independent engine objects observe each other's uploads, replacements and deletes in synthetic SQLite tests. Missing uploaded chunks can be restored from encrypted source. Full suite: 150 passed in 6.62 s; Ruff and compileall passed.
- Real PostgreSQL multi-process, outage, migration/backup and representative-corpus performance tests are NOT DONE. DATA-04 stays in progress. No staging database or student data was touched.
- Commit `371c8ce` was pushed to the existing draft PR. Its two CI test checks passed. The clean Git-archive ZIP passed CRC, checksum, extracted 150-test suite, Ruff, compileall and original image hashes. A delivery report and checksum were saved outside the repository.

## 2026-10-13, 16:23 Asia/Shanghai — ADR-011 and first web/API slice

- Recorded the owner's AI-native modular-monolith decision; updated roadmap and queue without dropping completed security/data work. Added detailed event/mastery/recommendation and secure BFF contracts.
- Added read-only FastAPI v1 adapter with typed DTOs, private BFF key, current-user session validation, revocation/role refresh and no mutating routes. Three contract tests passed. Streamlit code and journeys were not changed.
- Began Next.js/React/TypeScript read-only Home/Courses slice. The exact campus and tower assets were copied byte-for-byte into `web/public`. `npm run typecheck`, `npm run build` and `npm audit --audit-level=high` passed. Local browser desktop/mobile Home/Courses were rendered and inspected against an isolated synthetic SQLite catalog; no real student data was touched.
- Added owner-priced conservative daily provider-cost reservations to the existing shared counters. Synthetic weighted budget and missing-price tests pass; this is not a billed-cost guarantee or provider-side hard cap.
- Full Python suite: 156 passed with one upstream FastAPI/Starlette TestClient deprecation warning. Ruff, compileall, Bandit and pip-audit passed. Real PostgreSQL, secure cookies/CSRF, gateway, production deployment and paid calls were not tested/performed.

## 2026-10-13 — INT-01 event/projection slice

- Local previous milestone committed as `fbd8cdc`; it was not pushed. Added revision `20261013_06`, minimal quiz evidence and transactional outbox marker in the existing quiz write transaction, plus deterministic topic-level course mastery replay.
- Synthetic tests cover multi-course same-topic isolation, ambiguous attempt exclusion, payload privacy, duplicate append, replay of out-of-order event times, transaction rollback and SQLite migration round-trip. Focused 4 tests and full 160-test suite passed; one upstream TestClient deprecation warning. Full Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities.
- Not complete: concept-level evidence, corrected/superseded events, retention/deletion policy, database-level append-only controls, recommendation activation, outbox worker, real PostgreSQL migration and staging. Streamlit behavior and legacy global mastery remain unchanged. No GitHub push or deployment.
