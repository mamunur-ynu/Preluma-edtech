# Reproducible Baseline

Date: 2026-10-13 (Asia/Shanghai)

## Authoritative source

- Archive: `Preluma-edtech-v5.1-ui-refined.zip`
- Archive SHA-256: `3d96232b3dc58d1175548405e4b0d25ada5adb90aaab821d2bdfee86a81004bc`
- Archive integrity: `unzip -t` — PASS
- Extracted into a new working directory; the source ZIP and prior working folder were not modified.
- Baseline files: 128 regular files
- Python files: 101
- Test modules: 19

Required assets:

| Asset | SHA-256 | Result |
|---|---|---|
| `assets/ynu_campus.jpg` | `35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc` | MATCH |
| `assets/sidebar_bg.jpg` | `3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2` | MATCH |

## Runtime

- macOS / arm64 execution host
- Python `3.12.15`
- pip `26.2.1`
- Streamlit `1.65.0`
- pytest `9.1.1`
- Ruff `0.17.0`

Python 3.10 was not installed and was not tested. PostgreSQL and production Supabase credentials were not supplied.

## Baseline commands and observed results

```bash
python --version
python -m streamlit version
python -m ruff check .
python -m pytest -q
python -m compileall -q .
```

| Check | Observed result |
|---|---|
| Ruff | PASS — `All checks passed!` |
| Pytest | PASS — `103 passed in 3.39s` |
| Syntax compilation | PASS — 101 files, 0 errors |
| Streamlit AppTest | PASS — 0 application exceptions |
| AppTest warning | Expected bare-mode `missing ScriptRunContext`; not an app exception |

## Entry points and module inventory

- UI: `streamlit_app.py` → `app.py` → role-gated `views/`
- Presentation: `components/`
- Use cases: `services/`
- Learning/algorithm core: `core/` plus compatibility shims in root
- Authentication: `auth/`
- AI/RAG: `ai/`
- Relational persistence: `database/`
- Legacy compatibility persistence: `homework_core.py`, `project_core.py`, `storage_core.py`
- CI: `.github/workflows/ci.yml`; a half-hour keep-alive workflow was present

## Baseline risk ranking

| Priority | Finding |
|---|---|
| High | localStorage plus temporary URL query authentication token; no secure HttpOnly cookie path in plain Streamlit |
| High | homework/projects/announcements/profile extras remain name-keyed CSV/Supabase records |
| High | uploaded RAG documents lacked enforced actor/course visibility in service/retrieval paths |
| Medium | uploads largely trusted extension/filename and project blobs allowed 100 MB |
| Medium | some untrusted legacy values entered `unsafe_allow_html=True` without escaping |
| Medium | admin/reset services accepted actor username rather than validated actor identity |
| Medium | no Alembic migration or auditable idempotent legacy importer |
| Medium | CI linted a subset and had no security/dependency checks |
| Low | keep-alive workflow ran every 30 minutes and hid all curl failures |
| Low | brittle source-substring UI tests remained |

The baseline report records observations only; fixes and remaining risk are in the other release reports.
