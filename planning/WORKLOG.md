# Worklog

## 2026-10-14 — UI-01 Streamlit readability slice

- Removed the sidebar-wide `display:none` rule for widget labels and raised contrast for LEARN/TEACH expander headings, dashboard secondary text, home metric labels and footer text. Added a regression test for label visibility, focus-visible styles and opaque text contrast against the dark theme. No navigation or business logic changed.
- Focused UI/Streamlit tests: 14 passed. Full suite: 189 passed with one upstream TestClient warning. Ruff, compileall, `B311`-excluded Bandit, pip-audit and `git diff --check` passed. Both original campus/tower assets and Next.js copies retained their recorded SHA-256 hashes.
- Launched a disposable local Streamlit preview and inspected signed-in student Home at desktop 1440px and mobile 390px. The campus hero and tower sidebar rendered; the mobile document scroll width equalled 390px viewport width; LEARN heading computed as `rgb(185, 205, 226)`. Original student navigation remained usable. This was local HTTP, not a production/HTTPS check. Teacher/admin rendered pages and a full keyboard-navigation audit remain open, so UI-01 stays IN_PROGRESS.
- Commit `bf3a6b5` was fast-forward pushed to existing draft PR #2; both CI `test` checks passed. Its clean ZIP passed CRC, extracted 189 tests/Ruff and original-image hashes; SHA-256 `4ed2b4a8f28448f6c0d9bf2e997c6d923b8bec9ca6aeabad2be19140e8076a7b`. No deployment or merge.

## 2026-10-14 — INT-02 manual quarantine authorization and attribution

- Required a live, revocable session for an active administrator before the opt-in quarantine operation; no caller-provided actor ID is trusted. Revision `20261014_08` adds a nullable operator FK to the marker. Legacy quarantine rows retain a null operator, and downgrade refuses to discard populated attribution. No UI/API mutation or background worker was enabled.
- Synthetic negative tests cover missing/invalid, teacher, revoked, deactivated and demoted sessions; configured admins remain allowed. The SQLite migration test checks FK creation, legacy-null preservation and guarded downgrade. Focused tests: 12 passed before the added demotion case; final full suite: 188 passed with one upstream TestClient warning. Ruff, compileall, `B311`-excluded Bandit, pip-audit over both requirements files, Alembic single-head and `git diff --check` passed. Both original images and their Next.js copies match the recorded SHA-256 hashes. Real PostgreSQL, retention policy and tamper-resistant audit remain unverified.
- Commit `0b13363` was fast-forward pushed to the existing draft PR #2, not merged. Its clean source archive passed CRC, extracted 188 tests and Ruff, and preserved both exact image hashes. SHA-256: `0e9a9d5b5d8bcf43f34f62a58fe06313280102975edd16941a7ca16d1f80c066`. Both PR `test` checks subsequently completed successfully. No deployment or student-data mutation.

## 2026-10-14 — INT-02 explicit poison-event containment

- Added revision `20261014_07` with nullable quarantine timestamp/reason on outbox markers, and a narrow operator-invoked function that quarantines only deterministically invalid pending evidence or unsupported schema. Replay now validates course-less quiz events before acknowledging them and skips quarantined markers; it never deletes or marks bad evidence delivered. A valid event is not quarantined. Other courses can replay while an affected course remains fail-closed.
- Synthetic tests cover corrupt and unsupported events, valid-event refusal, ambiguous-course validation, unrelated-course progress, and revision 07 SQLite upgrade/downgrade. Downgrade refuses to discard populated quarantine metadata. Focused learning/outbox/migration/recommendation suite: 20 passed before this additional migration guard; focused migration/outbox suite after it: 9 passed. Final full Python suite: 185 passed with one upstream TestClient deprecation warning. Ruff, compileall, repository Bandit (`B311` excluded) and pip-audit over both requirements files passed; Alembic reports one head `20261014_07`.
- ADR-016 defines quarantine as containment, not correction. Append-only compensating correction, operator identity/alerts, same-course resume, PostgreSQL concurrency/outage rehearsal and retention/erasure remain open. No scheduler, real student data, provider, deploy or merge. Commit `a9edcfb` was fast-forward pushed to existing draft PR #2 on the owner's explicit update request; both PR test checks passed and an evidence-based milestone comment was posted. Its clean ZIP passed CRC, extracted 185 tests/Ruff, clean `npm ci`, Next typecheck/build, image hashes and checksum verification.

## 2026-10-14 — WEB-02 local browser sign-in and rendered layout

- Added an accessible, same-origin sign-in form and CSRF-backed sign-out control to the read-only Next.js `/my-learning` preview. The BFF keeps the session in an HttpOnly cookie; the client receives no raw session token. The private course preview remains server-rendered, and no Streamlit learning workflow changed.
- Inspected rendered Home and My learning pages in the local in-app browser at 1440px and 390px viewports. The exact campus/tower images were visibly present, their local routes returned HTTP 200 `image/jpeg`, and document width equaled viewport width at both sizes. With a disposable synthetic SQLite learner, browser sign-in displayed the enrolled course and sign-out returned to the sign-in form. An initial sign-out left browser-restored credential fields populated; controlled form state fixed this and a repeated browser run showed both fields blank. This validates local development-loopback behavior only, not HTTPS/gateway staging.
- The BFF synthetic HTTP smoke passed after updating anonymous/revoked-page assertions. Full Python suite: 180 passed with one upstream TestClient deprecation warning; Ruff and compileall passed. Next typecheck and production build passed; npm audit found zero vulnerabilities and pip-audit found no known vulnerabilities. Bandit high-severity gate (`-lll`) passed; unrestricted Bandit still reports 15 existing low-severity `B311` pseudorandom quiz/demo findings, with no medium/high findings. The `cedf003` Git-archive ZIP passed CRC, extracted 180 tests/Ruff, clean `npm ci` and extracted Next typecheck/build; image hashes matched. This documentation checkpoint will receive its own ZIP after commit. No production data, public deployment, paid provider or GitHub push.

## 2026-10-14 — synthetic learning/account deletion audit

- Added two isolated SQLite regression tests using disposable synthetic accounts only. Direct deletion of an otherwise unreferenced learner cascaded quiz attempt, learning event, outbox and mastery rows while retaining the independent course. A teacher with an uploaded private document could not be deleted because the uploader foreign key blocked it; the transaction rolled back and the document/account remained. Focused suite: 2 passed; no application delete endpoint was introduced.
- ADR-015/DATA-06 record that this is **not** a complete account-erasure feature. Policy and isolated PostgreSQL plus encrypted-source/index/object-store/backup rehearsal are required before implementing or advertising deletion. Deactivation is access control, not erasure. Combined full Python suite: 180 passed (one upstream TestClient warning); Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities.

## 2026-10-13 — INT-02 local source/projection integrity guard

- Added ADR-014 and validation that a v1 quiz event still matches its source attempt: producer/key, source ID, user/course/lesson, occurrence time, topic, score/total/percentage and unique well-formed concept aggregates. Duplicate append now verifies existing evidence. Replay and shadow recommendation reads reject drift; the recommendation API returns a generic 503 instead of returning a corrupt or cross-course citation. Recommendation reads also compare projection count/last event with the stream to catch a moved or missing event.
- Four synthetic corruption cases (course reassignment, score tampering, missing source and duplicate concepts) plus an API payload-leak test passed. Focused learning/API suite: 17 passed. Full Python suite: 178 passed with one upstream Starlette TestClient deprecation warning. Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities. Streamlit and Next.js code were not changed in this milestone.
- Still open: database-enforced append-only controls, compensating correction policy, source/event joint deletion detection, retention/account deletion, poison-event quarantine, teacher evaluation and real PostgreSQL staging. No production data, provider calls, deploy or GitHub push.

## 2026-10-13 — WEB-02 server-rendered private course preview

- Added `/my-learning`, a read-only Next.js server component that reads the first-party HttpOnly session cookie on the server, obtains `/v1/me` and `/v1/me/courses` through the private BFF transport, validates typed DTOs, and renders only enrolled courses. The raw session token is never intentionally passed to a client component or HTML. Streamlit remains the functional learning application; there is still no web login page.
- `npm run typecheck` and `npm run build` passed; the new page is a dynamic server-rendered route. `npm audit --audit-level=high` found zero vulnerabilities. The full Python suite again passed 173 tests (one upstream TestClient warning); Ruff, compileall, Bandit and pip-audit passed. A local synthetic SQLite account and enrolment were used with loopback FastAPI + Next development servers; the extended HTTP smoke passed anonymous/private/revoked page assertions and the existing login/CSRF/rotation/logout checks. It also checked that the raw cookie token did not appear in response HTML. Both local servers were stopped afterward. No real student data or paid service was used.
- An initial `next start` HTTP smoke returned 503 because production-mode configuration correctly requires HTTPS; the same synthetic smoke passed under `next dev`. This is **not** a rendered-browser HTTPS cookie test or a visual inspection of the new page. Gateway, real browser, mobile/desktop private-page rendering, authenticated role parity and production deployment remain open. No GitHub push or merge.

## 2026-10-13 — API-03 enrolled-course shadow recommendation contract

- Added a versioned, typed, read-only `GET /v1/me/courses/{course_id}/recommendation` endpoint over the existing explainable rule service. It derives the learner from the revocable server session, reuses BFF-key admission, and returns 403 for a course outside the enrolment boundary. No learning mutation or UI activation was added.
- Two new synthetic API tests cover missing/wrong BFF admission, missing/revoked/deactivated sessions, other-user/course denial, OpenAPI shape, no-store response, method safety and exclusion of raw quiz questions/answers. Focused API/rule suite: 8 passed. Full Python suite: 173 passed with one upstream Starlette TestClient deprecation warning. Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities.
- Both original image SHA-256 values remain unchanged. Real HTTPS browser/gateway, PostgreSQL RLS/concurrency, teacher rule evaluation and authenticated Next.js view remain open; no production data, deployment, paid provider or GitHub push was involved.

## 2026-10-13, 21:42 Asia/Shanghai — ADR-013 and opt-in outbox replay

- Aligned ROADMAP/TASK_QUEUE with the approved AI-native modular monolith, event-driven processing and learning-intelligence sequence without discarding completed security/API/Next work. Security, data isolation and isolated PostgreSQL staging remain first-order gates.
- Added a one-event outbox replay function; it atomically rebuilds an attributed learner/course mastery projection and marks delivery, while errors roll back both. PostgreSQL query paths use `FOR UPDATE SKIP LOCKED` and a transaction-scoped learner/course advisory lock; SQLite remains single-process evidence only. No daemon, Redis, external publish, live database or production data was touched.
- Added synthetic tests for idempotent retry, ambiguous course exclusion and failed-replay rollback. Focused event/outbox suite: 7 passed. Full Python suite: 171 passed with one upstream Starlette TestClient deprecation warning. Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities. The two original image hashes remain unchanged.
- Still open: real PostgreSQL multi-worker/locking and outage rehearsal, poison-event quarantine/retry/alerting, correction and deletion lifecycle, secure gateway/browser staging, teacher evaluation and release authorization. Draft PR #2 was not pushed or merged.

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

## 2026-10-13 — INT-01 concept evidence and shadow recommendations

- New quiz events now contain only per-concept aggregate correct/total counts (no raw questions/answers). Course replay produces separate topic and concept rows, preserving topic-only replay for earlier events. No schema migration was needed beyond revision 06.
- Added an active-enrollment-scoped, read-only next-step rule service with versioned `cold_start`, `provisional_practice`, `practice`, `review`, `course_ready` and `empty_course` decisions. It reports score/count, exact recent evidence event IDs and a plain-language reason. The existing Streamlit plan/UI was not switched to it.
- Focused event/rule tests: 7 passed. Full suite: 164 passed with one upstream TestClient warning. Ruff, compileall and Bandit passed; pip-audit found no known vulnerabilities. No paid provider, real data, PostgreSQL, GitHub push or deployment.

## 2026-10-13 — API-02 / WEB-01 local authentication boundary

- Added BFF-key-only typed FastAPI login/rotate/logout; login reuses the existing credential throttle and atomically replaces an existing browser token, rotation conditionally consumes the old token. Learning/catalog APIs remain read-only and Streamlit is unchanged.
- Added Next.js auth route handlers for exact configured Origin, bounded JSON login body, first-party `__Host-preluma_session` (`HttpOnly; Secure; SameSite=Lax; Path=/`) and session-bound HMAC CSRF proof. No token is returned in browser response JSON; no login page is active. Local synthetic HTTP smoke covers cookie flags, negative Origin/CSRF, re-login/rotation replay and logout revocation. Initial smoke failed only because an earlier local Next dev process held the build lock; it was stopped and rerun successfully.
- FastAPI focused auth/API tests: 7 passed; final full suite 168 passed (one upstream TestClient warning). Ruff, compileall, Bandit and pip-audit passed. Next TypeScript and production build passed; npm audit found zero vulnerabilities; synthetic build-time secrets were absent from `.next/static` (exact-value scan). The repeat local HTTP smoke passed after adding wrong-password, oversized-body and forged-CSRF cases.
- Commit `05e542d` was saved locally, not pushed. Its clean archive passed CRC and, after extraction, 168 Python tests, Ruff, `npm ci`, Next build/typecheck and both image hashes. A documentation-only checkpoint follows; rebuild an archive for final HEAD.
- Limitations: localhost HTTP smoke manually sends cookies; it is **not** a rendered-browser HTTPS cookie test. Private TLS/gateway/IP limits, role elevation and authenticated web view parity remain unverified. No production data, paid services, GitHub push or deployment.
