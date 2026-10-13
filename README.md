# Preluma EdTech v5.1 — Release-Hardened Streamlit Edition

**Light Up Before Class.** Preluma is a Yunnan University pre-class learning platform built with Python and Streamlit. Students prepare through a five-step Mission, adaptive quizzes, grounded AI tutoring, homework and projects; teachers receive course and class insight; administrators manage accounts and controlled password recovery.

This package is the release-hardening continuation of the refactored v5.1 codebase. Streamlit remains the working UI. The framework-independent `auth/`, `services/`, `core/`, `ai/`, `database/` and `security/` layers are designed to support a later incremental FastAPI/Next.js migration.

## Preserved identity

- Home hero: `assets/ynu_campus.jpg`
  - SHA-256 `35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc`
- Sidebar tower: `assets/sidebar_bg.jpg`
  - SHA-256 `3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2`
- Preluma, Yunnan University, “Light Up Before Class”, and “Prepare before class / Understand more during class” messaging
- Dark navy and cyan academic-technology design

The two required images are regression-tested byte-for-byte and embedded from module-relative paths so deployment does not depend on the process working directory.

## Capabilities

### Students

- Register, sign in, sign out, reset a password using a teacher/admin-issued one-time code
- Dashboard with mastery, streak, XP, achievements and deterministic recommendations
- Courses, enrolment, prerequisite-aware lessons and progress
- Five-step Mission: Brain Brief → example → practice → mock test → overview
- RAG-grounded AI Tutor with source citations and offline fallback
- Homework, feedback, notifications, projects, uploads, profile and analytics

### Teachers

- Class and course analytics, student drill-down and teacher workspace
- Create courses and homework; review submissions and weak concepts
- Upload/delete knowledge documents with role and ownership enforcement
- Announcements, project review and teacher profiles

### Administrators

- User inventory and role-aware access
- Deactivate accounts with immediate session revocation
- Issue one-time reset codes; a new code invalidates earlier unused codes
- Health/configuration overview without exposing secret values

## Security changes in this release

- Persistent browser session restoration is **disabled by default**. The old localStorage/query-token bridge is available only when `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION=true` is explicitly set for a classroom demo. It is a documented production blocker because Streamlit cannot create a first-party `HttpOnly`, `Secure`, `SameSite` authentication cookie.
- Admin/reset services accept a validated numeric actor identity rather than a caller-supplied actor username.
- Uploads have central extension, byte-limit, basename and file-signature validation; private local uploads use atomic content-addressed writes.
- Project uploads are capped at 25 MB. Knowledge documents and profile images have narrower policies.
- AI requests have an in-process per-user sliding-window limit. A reverse proxy/shared limiter is still required for multi-worker production.
- RAG filters visibility before returning passages. Public, private, staff and course scopes are enforced; knowledge-document deletion is owner/admin restricted.
- Retrieved course documents are treated as untrusted prompt data. Prompt-like instructions in documents must be ignored, and citations must correspond to retrieved sources.
- Conversation history is user-scoped, revocable and purged after the configured retention period (30 days by default).
- Dynamic project, profile and class-dashboard HTML values are escaped.

See [`reports/SECURITY.md`](reports/SECURITY.md) for evidence and remaining blockers.

## Requirements

- Primary verified runtime: Python 3.12
- Declared compatibility: Python 3.10+
- Python 3.10 was not available in the delivery environment and is therefore **not verified** in this release.

## Local installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                     # optional reference; export values through your shell
streamlit run streamlit_app.py
```

Open `http://localhost:8501`. With no API keys, the tutor uses the curated offline fallback. The default SQLite database under `data/` is disposable local/demo storage only.

Create the first account without putting a password in shell history:

```bash
python scripts/create_user.py admin "Project Owner" --role admin
```

## Configuration

Use environment variables or Streamlit secrets. Never commit `.env` or `.streamlit/secrets.toml`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL; SQLite by default, PostgreSQL required for persistent staging/production |
| `PRELUMA_ADMIN_USERS` | Comma-separated admin usernames |
| `PRELUMA_TEACHER_INVITE_CODE` | Optional teacher invite; unset disables teacher self-registration |
| `PRELUMA_SESSION_TTL_HOURS` | Server-side session lifetime |
| `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION` | Demo-only opt-in to the localStorage/query restore bridge; default `false` |
| `PRELUMA_AI_REQUESTS_PER_MINUTE` | Single-process AI request budget; default `12` |
| `PRELUMA_CONVERSATION_RETENTION_DAYS` | Tutor conversation retention; default `30` |
| `PRELUMA_LLM_TIMEOUT`, `PRELUMA_LLM_MAX_TOKENS` | Provider timeout/output caps |
| `PRELUMA_EMBEDDINGS` | `auto`, `hashing`, or optional `sentence-transformers` |
| `PRELUMA_VECTOR_STORE` | `auto`, `memory`, or optional `faiss` |
| `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. | Optional LLM providers; never required for offline mode |
| `SUPABASE_URL`, `SUPABASE_KEY` | Legacy compatibility storage only; review RLS before use |

All supported placeholders are listed in `.env.example` and `.streamlit/secrets.example.toml`.

## Database migrations

Back up the database before running any schema command. New local databases are created from current SQLAlchemy metadata. An existing v5.1 database can be upgraded with the reviewed Alembic migration:

```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME'
alembic current
alembic upgrade head
```

For a pre-Alembic database, follow [`reports/DATA_MIGRATION.md`](reports/DATA_MIGRATION.md) before stamping or upgrading. Do not stamp an unknown production schema without inspecting it.

Revision `20261013_02` records the course/lesson for future quizzes. Older attempts with a lesson ID are backfilled; older attempts without evidence remain unattributed and do not appear in course-specific teacher quiz metrics. Rehearse this revision and rollback on an isolated database copy before any production migration.

Legacy CSV import is dry-run by default:

```bash
python scripts/import_legacy_data.py --source-dir /path/to/copied-data \
  --report /tmp/preluma-import-dry-run.json

# Only after reviewing counts, ambiguous identities and backups:
python scripts/import_legacy_data.py --source-dir /path/to/copied-data \
  --apply --backup-dir /safe/preluma-backups \
  --report /safe/preluma-backups/applied-report.json
```

The importer is idempotent, creates source checksum manifests and quarantines missing/ambiguous identity relationships instead of guessing by full name. This delivery did **not** import or modify production data.

## Quality gates

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
pytest -q --cov=auth --cov=ai --cov=core --cov=database --cov=services --cov=security
bandit -q -s B311 -r auth ai core database services security scripts -x tests
pip-audit -r requirements.txt
python -m compileall -q .
```

Observed delivery results are recorded in [`reports/FINAL_VERIFICATION.md`](reports/FINAL_VERIFICATION.md). The final pre-package run passed 114 tests; the packaged ZIP is re-tested separately before release.

## Architecture and deployment

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FUTURE_FASTAPI_NEXTJS_MIGRATION.md`](docs/FUTURE_FASTAPI_NEXTJS_MIGRATION.md)
- [`STAGING_VALIDATION_CHECKLIST.md`](STAGING_VALIDATION_CHECKLIST.md)
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)

## Important limitations

- Homework/projects/announcements/profile extras still run through compatibility adapters backed by legacy CSV/Supabase storage. Relational target tables and a safe importer now exist, but production cutover is intentionally blocked until real-data reconciliation is reviewed.
- The persistent Streamlit browser-session bridge is not production-safe and is off by default. Use an external auth gateway or the future FastAPI transport with secure cookies.
- Each ordinary login now has a revocable server session. Open tabs refresh identity on every rerun, so account deactivation, password change and role change take effect without relying on stale UI state.
- PostgreSQL, Supabase RLS, production object storage, paid/live LLM calls and real production credentials were not available and are **not verified**.
- The default hashing embedder is a reliable lexical/offline fallback, not evidence of semantic retrieval quality.
- Existing screenshots under `docs/` are historical. Current desktop/tablet/mobile pages were visually inspected during this release, but the browser capture interface did not provide a filesystem export for new screenshot files.

## GitHub review

This release is published on `feature/preluma-release-hardening` for review against `main`. Review the pull request, require passing CI, and verify that no secret or runtime data file is present before merging. The branch is not a production deployment; the staging and security blockers above still apply.
