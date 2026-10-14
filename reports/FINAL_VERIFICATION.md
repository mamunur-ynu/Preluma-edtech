# Final Verification Evidence

Date: 2026-10-13 (Asia/Shanghai)

This file distinguishes checks executed in the delivery environment from checks that require external staging resources.

## Executed locally

| Check | Command / method | Result |
|---|---|---|
| Ruff | `python -m ruff check .` | PASS — all checks passed |
| Tests | `python -m pytest -q` | PASS — 114 passed in 4.57 s in the working tree; 114 passed in 4.16 s from a fresh ZIP extraction |
| Coverage | `pytest --cov=auth --cov=ai --cov=core --cov=database --cov=services --cov=security` | PASS — 83% combined for measured backend layers; 111-test checkpoint before final added tests |
| Bandit | `bandit -q -r . -x ./tests -s B311` | PASS — no reported findings from the extracted package; intentional low-risk UI fallbacks are individually annotated, and B311 is excluded only for non-security educational/demo randomisation |
| Dependency audit | `pip-audit -r requirements.txt -r requirements-dev.txt` | PASS — no known vulnerabilities found |
| Alembic upgrade | upgrade copied v5.1 SQLite schema to `20261013_01` | PASS — all target tables and RAG provenance columns present |
| Alembic downgrade | `alembic downgrade base` on the test copy | PASS — new targets removed |
| Python syntax | `py_compile` over every packaged Python file | PASS — 116 files, 0 errors |
| Streamlit AppTest | `pytest -q tests/test_runtime_streamlit.py` | PASS — 6 passed in 3.10 s from a fresh ZIP extraction |
| Actual browser | isolated localhost Streamlit server | PASS — student, teacher and admin login/routes rendered; browser console errors: 0 |
| Desktop | browser default (~968×720 capture; original target previously verified at 1440×1000 in v5.1 UI pass) | PASS — campus and tower visible, dashboard/teacher/admin pages usable |
| Tablet | explicit 820×1180 viewport | PASS — hero/sidebar/cards responsive and readable |
| Mobile | explicit 390×844 viewport | PASS — hero stacks, metrics become two columns, collapsed navigation remains available |
| Required image hashes | SHA-256 | PASS — exact required values |

Actual rendered screenshots were captured and inspected through the browser tool. That interface displayed image bytes but did not provide a filesystem export path, so no new after-screenshot files are included. Existing `docs/*.png` screenshots are historical and are not presented as this release's evidence.

## Package verification

The candidate archive was built with a single top-level `Preluma-edtech-vNEXT-final/` directory and 173 entries, then tested with `unzip -t`: PASS, no compressed-data errors. A fresh extraction passed Ruff, all 114 tests, all 6 Streamlit AppTests, compilation of 116 Python files, Bandit, Alembic history, excluded-artifact scanning and a high-confidence secret-pattern scan. Both packaged image hashes match the authoritative source assets.

The final archive is rebuilt after this report is written. Its SHA-256 is stored in the sibling `Preluma-edtech-vNEXT-final.zip.sha256` delivery file so the archive does not attempt to contain its own recursive checksum.

## Not run / externally blocked

| Check | Status | Reason |
|---|---|---|
| Python 3.10 runtime | NOT RUN | Python 3.10 interpreter unavailable; Python 3.12.15 is verified |
| Real PostgreSQL migration/concurrency | NOT RUN | no approved sandbox/staging instance or credentials |
| Supabase RLS deny tests | NOT RUN | no staging Supabase project/credentials |
| Production CSV/blob import | NOT RUN | no approved production export; production mutation prohibited |
| Live paid LLM provider calls | NOT RUN | no need to spend funds or expose real keys; router uses mocked tests/offline browser mode |
| Production deployment | NOT RUN | explicitly requires owner authorization |
| GitHub push/PR | NOT RUN | explicitly requires owner authorization |

## Readiness statement

The package is suitable for local demonstration, portfolio review and a controlled staging rehearsal. It is **not approved for real-student production use** until the High blockers in `reports/SECURITY.md` and `STAGING_VALIDATION_CHECKLIST.md` are closed with external evidence.
