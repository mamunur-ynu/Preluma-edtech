# Preluma Autopilot Roadmap

Source branch: `feature/preluma-release-hardening`; review target: draft PR #2. This roadmap is provisional until the owner-provided Autopilot master prompt is available in the workspace.

## Phase 1 — Security boundaries

Close reproducible authorization, RAG visibility, upload and session risks in the current Streamlit architecture. Use deny-by-default behavior for untrusted data. Keep negative tests alongside every fix.

## Phase 2 — Data durability and migration

Rehearse Alembic upgrade/downgrade and the dry-run importer on disposable PostgreSQL when an approved staging instance is available. Reconcile counts, identities and checksums before any cutover. Test private object-storage policies with separate student, teacher and anonymous identities.

## Phase 3 — Production transport and operations

Add a supported secure session gateway and shared abuse/cost limits in an isolated staging deployment. Verify HttpOnly, Secure and SameSite cookie behavior in a rendered browser. Add scheduled retention, backup/restore evidence and failure alerting.

## Phase 4 — Workflow and release evidence

Exercise student, teacher and admin workflows, real migration rehearsal, provider red-team/citation evaluation, responsive UI, accessibility, CI and clean package extraction. Keep the PR draft until all blocking evidence is recorded and reviewed.

External credentials, paid resources, production data, merge and deployment require separate owner authorization. Local code changes and synthetic-data tests can proceed now.
