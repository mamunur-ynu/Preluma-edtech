# Autopilot baseline audit

Date: 2026-10-13. Repository: `mamunur-ynu/Preluma-edtech`, draft PR #2. Starting review SHA `b13108a1c1f705ef98d64e755eddec0ca4decfc3`; the latest SEC-01 SHA is `1554f3d`.

- GitHub PR was confirmed draft against `main` with two successful CI runs on the starting SHA. The branch carries the modular v5.1 source; `main` is the earlier monolith.
- Previous release report claimed 114 tests, 6 AppTests, Ruff, Bandit and pip-audit success. They were rerun on the previous turn's final ZIP and passed; this run independently executed the full suite after SEC-01: 116 passed in 4.80 s. Focused security/AI tests: 27 passed in 1.45 s. Ruff, `compileall`, Bandit and pip-audit passed. The app tests are included in the full suite; they use synthetic SQLite and offline/mocked providers.
- Asset SHA-256 checks from the current checkout matched both required values in `AGENTS.md`.
- Python 3.12.15 was used. Python 3.10, real PostgreSQL, Supabase RLS/private object storage, live paid LLMs, secure gateway, staging and production were NOT RUN here.
- Open risks: secure browser session transport, role/session refresh, shared rate limits, real migration/RLS evidence, data identity reconciliation, live-provider quality and historical credential rotation. See `reports/SECURITY.md` and `planning/TASK_QUEUE.md`.

No branch protection setting or third-party permission was changed. CI remains least-privilege; owner approval is required before changes to repository access settings.
