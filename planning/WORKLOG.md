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
