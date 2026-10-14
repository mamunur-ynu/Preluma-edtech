# Deploying Preluma v5.1

This release is ready for staging validation. Production deployment remains a deliberate, owner-authorized step.

## 1. Prepare an isolated staging environment

Use Python 3.12 and a dedicated PostgreSQL database. SQLite is suitable only for local demonstrations because it does not provide the concurrency and durability expected for a real class.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set `DATABASE_URL`, account policy settings, and only the AI provider keys you intend to use. Keep `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION=false`. Never commit `.env` or `.streamlit/secrets.toml`.

## 2. Back up and migrate the database

Take a provider-native PostgreSQL backup before applying schema changes. Then run:

```bash
alembic upgrade head
alembic current
```

For legacy CSV data, start with a dry run:

```bash
python scripts/import_legacy_data.py --source-dir /path/to/legacy-data
```

Review the summary and quarantine output. Apply only after creating a separate backup directory:

```bash
python scripts/import_legacy_data.py \
  --source-dir /path/to/legacy-data \
  --backup-dir /path/to/immutable-backup \
  --apply
```

The importer records source hashes and stable legacy identifiers so an identical rerun is idempotent. Ambiguous or missing identities are quarantined rather than guessed.

## 3. Run release gates

```bash
ruff check .
pytest -q
python -m compileall -q .
bandit -q -r . -x ./.venv,./tests -s B311
pip-audit -r requirements.txt -r requirements-dev.txt
```

Launch staging with:

```bash
streamlit run app.py --server.address 127.0.0.1
```

For a remote environment, put Streamlit behind an HTTPS reverse proxy or trusted platform gateway. Do not expose a plain HTTP development server to the internet.

## 4. Validate roles and workflows

- Student: login, Home, Dashboard, Courses, AI Tutor, and a complete Mission.
- Teacher: Teacher Dashboard, Homework Center, course analytics, and knowledge-base upload.
- Admin: user activation, reset-code issuance, audit history, and system health.
- Confirm the campus hero and tower sidebar images load from `assets/`.
- Test desktop, tablet, and mobile widths.
- Confirm unauthorized users receive denial responses for teacher/admin actions and private RAG documents.

Use disposable staging accounts and non-sensitive sample data. Do not point validation at production.

## 5. Rollback

If an application regression occurs, stop the new application instance and restore the prior release artifact. If a schema rollback is also required, prefer restoring the pre-migration database backup. Alembic downgrade is available for the release revision, but a tested backup restore is safer when data has already been written by the new version.

```bash
alembic downgrade -1
```

Never run rollback or legacy import commands against production without explicit owner authorization and a verified backup.

## Streamlit Community Cloud notes

Use `app.py` as the main file and copy placeholders from `.streamlit/secrets.example.toml` into the platform secret manager. A persistent PostgreSQL `DATABASE_URL` is required for real users; the bundled SQLite default may be reset during redeploys. Run migrations from a controlled release job before switching traffic.

GitHub publication of a review branch does not deploy the app, rotate live credentials, or modify production data.
