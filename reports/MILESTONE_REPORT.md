# Autopilot milestone report

Updated: 2026-10-13, Asia/Shanghai. Branch `feature/preluma-release-hardening`, draft PR #2. Exact current commit SHA is available from `git rev-parse HEAD`; the preceding SEC-01 commit is `1554f3d`.

## Completed in this milestone

- SEC-01: unlabeled RAG uploads fail closed; curated topics are explicitly public; document indexing requires active staff and scopes duplicate bytes by owner, course and visibility.
- SEC-02: every login has a server session, every Streamlit rerun revalidates it, open tabs lose access after deactivation/password change, and role changes refresh. Active-account and enrollment checks protect affected AI/course/learning/recommendation services.
- SEC-04: teacher analytics and student drill-down require active teacher/admin actors; teachers see only owned or shared-course rosters, and mistake counts no longer include other teachers' students. Course selectors reflect that same authorization.
- DATA-02: reconcile uploaded-document vectors against authoritative database metadata on startup, remove orphan/tampered chunks, mark lost chunks for re-upload, and delete vectors before committing document removal.
- SEC-03 partial local hardening: bound reset-code issuance and unify chat/tutor per-user request budget. A shared multi-worker limiter and per-provider spend ceilings are **not** complete.
- DATA-03: preserve course/lesson context on new quiz attempts; course-launched Mission carries that context, ambiguous attempts stay unattributed, and teacher analytics use course-filtered quiz activity rather than mixed global mastery.
- The repository now has durable `AGENTS.md` and the planning queue, worklog, current-state checkpoint, release gates and decision log specified by the owner.

## Verification actually executed

| Check | Outcome |
|---|---|
| Full Pytest | 135 passed in 6.43 s (latest DATA-03 run) |
| Auth/security focused tests | 30 passed in 1.34 s |
| Course provenance migration and workflow | Synthetic upgrade/downgrade, multi-course isolation and course-to-Mission AppTest passed |
| SEC-04 + Streamlit runtime focused tests | 13 passed in 4.68 s |
| AI/security/recovery focused tests | 33 passed in 1.24 s before the final delete-order regression was added |
| Role and login Streamlit AppTests | 10 passed in 4.23 s |
| Ruff | PASS |
| Python compileall | PASS |
| Bandit (B311 demo randomness excluded) | PASS |
| pip-audit for runtime and dev requirements | No known vulnerabilities found |
| Campus/tower SHA-256 | Both match the required values in `AGENTS.md` |
| Clean ZIP extraction | 132 tests passed in 5.90 s, Ruff passed, both image hashes matched; archive CRC and SHA-256 valid. |

These tests use synthetic SQLite data and offline/mocked AI. Python 3.10, real PostgreSQL, RLS/private object storage, live paid providers, secure gateway and staging/production were NOT RUN. Current release status remains `DEMO_READY`, with production/pilot blockers listed in `planning/RELEASE_GATES.md`.

Course views now isolate attributed quiz activity for students enrolled in multiple courses. Personal mastery remains global; teacher charts intentionally show course quiz averages instead. Historical attempts without an explicit course/lesson cannot be reliably assigned and are excluded from course metrics pending reviewed data reconciliation (DATA-05).

The uploaded-document source bytes are not retained, so a lost index cannot be rebuilt automatically; owners must re-upload. JSON vector persistence is process-local and not safe as a coordinated multi-worker index. DATA-04 tracks that production blocker.

Login/reset-failure, reset-issuance and AI request counters are still process-local. They do not cap provider failover calls or spending across workers. The production contract is in `docs/RATE_LIMIT_PRODUCTION_CONTRACT.md`; SEC-03 remains open.

Source package and SHA-256 checksum are delivered from `/Users/mim/Desktop/Preluma/Deliverables/`. Select the ZIP whose short SHA matches current `HEAD`; after any later commit, regenerate and reverify it. Draft PR #2 remains unmerged; check the latest CI run rather than assuming a prior run applies.

No merge to `main`, deployment, production data mutation or paid API call was performed.
