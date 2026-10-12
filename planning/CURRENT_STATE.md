# Current state and exact resume point

Updated: 2026-10-13, Asia/Shanghai

- Base SHA: `b13108a1c1f705ef98d64e755eddec0ca4decfc3` (first published vNEXT review commit).
- Current branch: `feature/preluma-release-hardening`, draft PR: <https://github.com/mamunur-ynu/Preluma-edtech/pull/2>.
- Latest completed tasks: SEC-01 at `1554f3d`, SEC-02 at `577c532`, and SEC-04 in the current milestone commit. Check `git log -1` for its exact SHA and `git status` before editing.
- Environment: macOS, Python 3.12.15 in `/private/tmp/preluma-v5-py312.iqqage`. The latest full local suite after SEC-02 was 123 passed in 5.60 s; 10 role/AppTests passed in 4.23 s; Ruff, compileall, Bandit and pip-audit passed. These checks used isolated synthetic SQLite and mocked/offline AI; they do not validate production infrastructure.
- Current issue: DATA-02 vector/metadata recovery after interrupted operations. See `planning/TASK_QUEUE.md` for acceptance and rollback.
- Next three executable tasks: DATA-02 vector/metadata recovery; SEC-03 shared rate-limit design and local contract tests; UI-01 dynamic HTML/accessibility review. Re-rank after each completed task and any new PR feedback.
- SEC-04 limitation: metrics are scoped to the authorized student roster and accessible course IDs, but `QuizAttempt`/`SkillProfile` do not record course provenance. A student enrolled in two courses contributes all of their attempts/mastery to either course view. DATA-03 is queued for a schema-backed remedy.
- External blockers: no approved isolated PostgreSQL/Supabase project, secure gateway, real-data export or live paid-provider budget. DATA-01 and AUTH-01 remain BLOCKED. Safe alternative: synthetic SQLite/service tests and local gateway design only.
- Schema: Alembic head `20261013_01`; copied SQLite upgrade/downgrade previously passed. Real PostgreSQL migration and backup/restore NOT PERFORMED. No risky uncommitted schema diff is intended for SEC-02.
- Deployments: staging NOT PERFORMED; production NOT PERFORMED. No merge to `main`, real-data mutation or paid API calls.
- Images: campus SHA-256 `35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc`; tower SHA-256 `3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2`.

**RESUME FROM HERE:** in `/Users/mim/Desktop/Preluma/Preluma-edtech-vNEXT-git`, run `git status --short --branch`, read `AGENTS.md` and this file, then implement DATA-02 with focused and full tests before updating draft PR #2.
