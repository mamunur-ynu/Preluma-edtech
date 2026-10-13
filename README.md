# Preluma EdTech v5.1 — Release-Hardened Streamlit Edition

**Light Up Before Class.** Preluma is a Yunnan University pre-class learning platform built with Python and Streamlit. Students prepare through a five-step Mission, adaptive quizzes, grounded AI tutoring, homework and projects; teachers receive course and class insight; administrators manage accounts and controlled password recovery.

This package is the release-hardening continuation of the refactored v5.1 codebase. Streamlit remains the working UI. ADR-011 establishes an incremental FastAPI/Next.js migration on the same modular Python service layer; the new API and web pages are an early slice, not a replacement for student/teacher workflows. Browser authentication routes exist for isolated testing, but there is no authenticated web journey or production gateway yet.

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
- SQLite demos use in-process AI limits; PostgreSQL uses shared database counters. A trusted gateway must still enforce IP-level quotas.
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

### Experimental web and private auth slice

The `api/` adapter and `web/` Next.js home/catalog run alongside Streamlit. To exercise them locally, use a **synthetic** database and the same random 32+-character `PRELUMA_BFF_SHARED_KEY` on both server processes. Start FastAPI with `python -m uvicorn api.app:app --host 127.0.0.1 --port 8765`, then in `web/` run `npm ci` and set server-only `PRELUMA_API_INTERNAL_URL`, `PRELUMA_BFF_SHARED_KEY`, `PRELUMA_PUBLIC_ORIGIN` and `PRELUMA_CSRF_SECRET` before `npm run dev`. The catalog requires the private API connection; the home page renders without it. Private API login/rotation/logout and Next.js BFF cookie/CSRF route handlers have **local synthetic tests only**; there is no login page or student/teacher web parity yet. Never place secrets in `NEXT_PUBLIC_*`, expose the FastAPI port publicly, or deploy this slice without an approved TLS/private-network gateway and browser staging checks. Run `pytest -q tests/test_api_contract.py tests/test_api_auth_contract.py`, `cd web && npm run typecheck && npm run build`; `npm run test:auth` additionally needs running local FastAPI/Next servers and synthetic credentials (`PRELUMA_WEB_BASE_URL`, `PRELUMA_TEST_USERNAME`, `PRELUMA_TEST_PASSWORD`). The contracts are in `docs/WEB_AUTH_BFF_CONTRACT.md` and `docs/LEARNING_INTELLIGENCE_CONTRACT.md`.

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
| `PRELUMA_AI_REQUESTS_PER_MINUTE` | Per-user AI request budget; default `12` |
| `PRELUMA_CONVERSATION_RETENTION_DAYS` | Tutor conversation retention; default `30` |
| `PRELUMA_LLM_TIMEOUT`, `PRELUMA_LLM_MAX_TOKENS` | Provider timeout/output caps |
| `PRELUMA_EMBEDDINGS` | `auto`, `hashing`, or optional `sentence-transformers` |
| `PRELUMA_VECTOR_STORE` | `auto` (database on PostgreSQL), `database`, local `memory`, or optional local `faiss` |
| `PRELUMA_BFF_SHARED_KEY` | Private FastAPI/Next.js server-to-server key (32+ random characters); never browser-exposed |
| `PRELUMA_PUBLIC_ORIGIN` | Exact first-party web origin for mutation Origin checks; HTTPS outside local development |
| `PRELUMA_CSRF_SECRET` | Independent 32+ character server-only key for session-bound CSRF proofs |
| `PRELUMA_PROVIDER_MAX_USD_PER_DAY`, `PRELUMA_PROVIDER_PRICES_JSON` | Owner-supplied conservative provider-cost admission policy; not an invoice-accurate spending guarantee |
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

Revision `20261013_03` retains encrypted extracted text for document-index recovery. PostgreSQL deployments must supply the same owner-managed `PRELUMA_DOCUMENT_KEY` to every worker; upload fails closed if it is absent. SQLite demos create a private key in `data/document_recovery.key`. Back up the key with the database: losing it makes encrypted sources unrecoverable. Existing uploads predating this revision need an owner re-upload before automatic recovery is possible.
The local `vector_index.json` still contains retrieval passages; keep the entire data directory on private, access-controlled storage. Encrypted recovery source does not make that process-local index a multi-worker or production-safe store.

Revision `20261013_05` adds a shared relational vector index. PostgreSQL workers use it automatically; they cannot opt into the process-local JSON store. Each search sees committed rows, and document replacement is one transaction. Uploaded chunk text is encrypted with the shared `PRELUMA_DOCUMENT_KEY`; curated public text stays readable. Existing uploaded rows with recoverable encrypted source are reindexed on first startup; legacy rows lacking source need one owner re-upload. Brute-force scoring is intended for classroom-sized corpora, not large-scale retrieval. Real PostgreSQL concurrency, key rotation and query-performance tests remain staging gates.

Revision `20261013_04` adds atomic database-backed rate-limit buckets. SQLite demos default to in-process limits; PostgreSQL requires shared database limits and an explicit `PRELUMA_PROVIDER_CALLS_PER_HOUR` before live provider calls. The latter limits HTTP attempts, not monetary spend. Gateway/IP controls, billed-cost reconciliation and real PostgreSQL concurrency/outage checks remain release gates.
An additional owner-priced cost reservation now requires `PRELUMA_PROVIDER_MAX_USD_PER_DAY` and exact `PRELUMA_PROVIDER_PRICES_JSON` entries for PostgreSQL live calls. It is an estimate rather than a guarantee of billed cost; account-side hard caps and alerts still need staging validation.

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
