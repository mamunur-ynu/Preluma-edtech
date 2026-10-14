# vNEXT Release-Hardening Changelog

Compared with authoritative `Preluma-edtech-v5.1-ui-refined.zip`.

## Removed

- `.github/workflows/keep-alive.yml` — removed the half-hourly wake-up request and its false-green `curl ... || true` behavior.

No application feature or source module was removed.

## Added

- `security/__init__.py`, `security/rate_limit.py`, `security/uploads.py`
- `services/upload_service.py`
- `services/homework_service.py`, `services/project_service.py`, `services/mission_history_service.py`, `services/audit_service.py`
- `database/legacy_repository.py`
- `scripts/import_legacy_data.py`
- `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/20261013_01_release_hardening.py`
- `tests/test_security_hardening.py`, `tests/test_legacy_migration.py`, `tests/test_architecture_boundaries.py`
- `docs/FUTURE_FASTAPI_NEXTJS_MIGRATION.md`
- `reports/BASELINE.md`, `reports/SECURITY.md`, `reports/DATA_MIGRATION.md`, `reports/FINAL_VERIFICATION.md`, `reports/CHANGELOG_VNEXT.md`, `reports/IMPLEMENTATION_REPORT.md`
- `STAGING_VALIDATION_CHECKLIST.md`, `PROJECT_STATE.md`

## Modified

### Authentication/security

- `config.py`, `.env.example` — legacy-browser-session flag, AI budget and conversation retention settings.
- `components/session_bridge.py`, `views/login.py` — persistent browser restore off by default and labelled demo-only.
- `auth/authentication.py`, `database/repository.py`, `services/user_service.py`, `views/admin.py` — actor-ID authorization, reset-code invalidation and session-safe administration.
- `project_core.py`, `services/media_service.py`, `views/homework.py`, `views/profile.py`, `views/projects.py` — content-aware upload handling and smaller limits.
- `views/class_dashboard.py`, `views/projects.py`, `views/profile.py` — escaping of user-managed HTML values.

### Persistence/migration

- `database/models.py` — RAG provenance and relational legacy target tables.
- `database/connection.py` — explicit defensive initialization failures.
- `requirements.txt`, `requirements-dev.txt` — bounded major versions plus Alembic/security/coverage tools.

### AI/RAG

- `ai/documents.py` — content-signature upload validation.
- `ai/rag_engine.py` — visibility filters and untrusted source blocks.
- `ai/prompts.py` — prompt-injection boundary and narrower JSON exception handling.
- `services/ai_service.py` — actor/course authorization, digest deduplication, scoped retrieval, retention and abuse limit.
- `views/ai_tutor.py` — authenticated knowledge-document management contract.

### Architecture/UI compatibility

- `app.py`, `views/home.py`, `views/homework.py`, `views/profile.py`, `views/class_dashboard.py`, `views/projects.py`, `views/mission.py`, `views/admin.py`, `views/teacher_studio.py`, `views/ai_tutor_legacy.py` — imports routed through service boundaries without removing visible features.
- `services/course_service.py`, `views/analytics.py` — teacher/admin ownership checks for course analytics.

### Tests/CI/docs

- `.github/workflows/ci.yml` — least-privilege permissions, concurrency, whole-tree lint, compile, Bandit and pip-audit.
- `tests/conftest.py`, `tests/test_auth.py`, `tests/test_ai.py`, `tests/test_runtime_streamlit.py` — new contracts and role smoke coverage.
- `tests/test_v24_polish.py`, `tests/test_v25_unique_design.py` — brittle source-substring tests replaced with behavioral/component contracts.
- `README.md`, `docs/ARCHITECTURE.md`, `DEPLOYMENT_GUIDE.md` — accurate install, architecture, risk and staging guidance.

## Backward-compatibility implications

- Streamlit user workflows and route names remain in place.
- `issue_reset_code` now requires a numeric actor ID rather than actor username.
- `user_service.set_active` now requires a numeric actor ID.
- `ai_service.list_documents` and `remove_document` require the authenticated actor ID.
- `course_completion_report` requires the authenticated actor ID.
- Persistent “keep me logged in” is disabled unless explicitly enabled for demo use.
- Project upload maximum changes from 100 MB to 25 MB.
- Legacy data remains readable through compatibility adapters; no production import/cutover occurred.
