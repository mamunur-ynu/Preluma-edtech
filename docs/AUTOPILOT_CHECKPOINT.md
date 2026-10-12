# Autopilot Checkpoint

Updated: 2026-10-13, Asia/Shanghai

## Resume location

- Repository: `/Users/mim/Desktop/Preluma/Preluma-edtech-vNEXT-git`
- Branch: `feature/preluma-release-hardening`
- Draft PR: <https://github.com/mamunur-ynu/Preluma-edtech/pull/2>
- Start commit: `b13108a1c1f705ef98d64e755eddec0ca4decfc3`
- Current task: SEC-02, as listed in `docs/TASK_QUEUE.md`. SEC-01 is implemented and locally verified; commit/push evidence appears in the Git log and PR checks.

## Resume procedure

1. Read `AGENTS.md`, this checkpoint, `docs/TASK_QUEUE.md`, `docs/WORKLOG.md`, and the complete Autopilot master prompt if it has arrived.
2. Run `git status --short --branch` and `git log -3 --oneline`; preserve unfinished changes.
3. Finish the highest-priority unblocked task, run focused tests and full gates, update the durable files, commit and push to the existing feature branch, and verify PR checks.
4. Continue to the next safe task. Do not merge or deploy.

## Current unknowns and boundaries

- Newly referenced Autopilot master prompt was not visible in the workspace at checkpoint creation. The owner has been asked to attach it or give its path.
- No authorized real PostgreSQL/Supabase staging credentials, production data or paid-provider budget are available.
- Current local suite after SEC-01: 116 tests, Ruff, Bandit, compile and pip-audit passed. Re-run after changes.

## Next concrete code steps

- Audit `services/ai_service.py` and `services/course_service.py` for active-user and course-enrollment checks on every private read/write path.
- Add negative regression tests for a deactivated account and a student who is not enrolled in a course.
