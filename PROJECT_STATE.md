# Project State

Updated: 2026-10-13

## Completed in this working copy

- Reproduced and recorded the v5.1 packaged baseline.
- Preserved and hash-verified the exact campus hero and illuminated tower assets.
- Added security settings, actor-ID admin/reset contracts, reset invalidation, upload validation, AI rate limiting, RAG visibility/ownership, prompt-injection boundaries and conversation retention.
- Added relational migration targets, Alembic upgrade/downgrade and a dry-run-first idempotent legacy importer with backups/quarantine.
- Routed legacy UI imports through service compatibility boundaries.
- Expanded CI and replaced brittle UI grep tests with behavioral contracts.
- Executed automated, migration, security, dependency and rendered role/viewport checks.
- Added architecture, migration, security, staging and future transport documentation.

## External blockers that remain

- Secure HttpOnly cookie/gateway integration for persistent production sessions.
- Real PostgreSQL staging and Supabase RLS/private object-storage validation.
- Owner-approved production export, identity reconciliation and relational cutover.
- Live-provider prompt-injection/citation evaluation with approved test credentials/budget.
- Python 3.10 verification if the declared lower bound must be formally certified.

## Publication and prohibited actions

- The owner authorized publication of the reviewed source on `feature/preluma-release-hardening` as a pull request against `main`.
- No direct modification of `main`, deployment or production data mutation was performed.
- No real secret was added to the project.

## Immediate continuation commands

```bash
cd /path/to/Preluma-edtech-vNEXT-final
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
streamlit run streamlit_app.py
```

For staging, follow `STAGING_VALIDATION_CHECKLIST.md`; do not skip its backup, dry-run or authorization steps.
