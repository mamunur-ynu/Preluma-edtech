# Preluma engineering instructions

This repository continues draft PR #2 on `feature/preluma-release-hardening`. The latest modular Streamlit implementation on this branch is the source of truth. Do not restore the older monolithic `main` application.

Before changing code, read `planning/CURRENT_STATE.md`, `planning/TASK_QUEUE.md`, `planning/WORKLOG.md`, and the relevant decisions in `planning/DECISION_LOG.md`. The owner-provided Autopilot master prompt is the governing specification; its complete text was read on 2026-10-13. Follow it if a local note differs.

Work from the highest-priority unblocked item in `planning/TASK_QUEUE.md`. Implement one reviewable change at a time, add meaningful regression tests, run the relevant tests and release gates, then update the queue, worklog, decision log and checkpoint with exact evidence. Continue to the next safe item while execution time permits. Record unknowns as unknown; do not mark inherited claims as checks performed now.

Preserve the Streamlit UI, modular service boundaries, all user workflows and the two original images:

- `assets/ynu_campus.jpg` SHA-256 `35705733aedb56eb3b95d64c4878c265247c7670a210be8405a3d18e81f6addc`
- `assets/sidebar_bg.jpg` SHA-256 `3343f66a4d9d90de2cf70cb274c819322fb92e2da9a1e79dabc646d8ac7113e2`

Do not commit secrets, generated data, local databases or personal records. Never modify production data, deploy, pay for services or merge into `main` without the owner's explicit approval. Keep draft PR #2 updated with tested feature-branch commits. No force-push.

Local release gates: `ruff check .`, `pytest -q`, `python -m compileall -q .`, `bandit -q -s B311 -r . -x ./tests`, and `pip-audit -r requirements.txt -r requirements-dev.txt`. Run commands from the repository root in an isolated Python environment. A passing local gate does not prove PostgreSQL, Supabase RLS, a live provider or a production deployment.
