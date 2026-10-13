# Staging Validation Checklist

Use a staging project containing no production student records. Record operator, timestamp, commit/ZIP SHA and evidence for every item.

## Before deployment

- [ ] Verify final ZIP SHA-256 and `unzip -t`.
- [ ] Scan the extracted archive for `.env`, `.streamlit/secrets.toml`, databases, logs, private records and API-key patterns.
- [ ] Provision a dedicated PostgreSQL database/user with least privilege and encrypted transport.
- [ ] Back up the staging database and test restore to a second database.
- [ ] Review Supabase/PostgreSQL RLS and app-level authorization; deny anonymous access to student documents and profiles.
- [ ] Provision private object storage; require authenticated/signed downloads and malware quarantine.
- [ ] Put Streamlit behind a supported secure authentication gateway. Keep `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION=false`.
- [ ] Configure gateway/shared rate limiting for login, reset and AI routes.

## Required secret names

- `DATABASE_URL`
- `PRELUMA_ADMIN_USERS`
- `PRELUMA_TEACHER_INVITE_CODE` (optional; leave unset to disable self-registration)
- `PRELUMA_SESSION_TTL_HOURS`
- `PRELUMA_ALLOW_LEGACY_BROWSER_SESSION=false`
- `PRELUMA_AI_REQUESTS_PER_MINUTE`
- `PRELUMA_CONVERSATION_RETENTION_DAYS`
- `PRELUMA_LLM_TIMEOUT`
- `PRELUMA_LLM_MAX_TOKENS`
- One or more optional provider keys (`GROQ_API_KEY`, `OPENAI_API_KEY`, etc.)
- `SUPABASE_URL` / server-side key only if the reviewed compatibility path is still required

Never paste values into reports, tickets, logs or screenshots.

## Migration rehearsal

- [ ] Export/copy legacy CSV/blob data without modifying the source.
- [ ] Run the importer in dry-run mode and archive the JSON report.
- [ ] Resolve every ambiguous/missing identity; do not map duplicate names automatically.
- [ ] Run `alembic current` and review the schema diff.
- [ ] Run `alembic upgrade head` on staging.
- [ ] Verify `20261013_02` retains historical ambiguous quiz attempts as NULL and backfills only explicit lesson-linked attempts; rehearse downgrade on a disposable restored copy.
- [ ] Run the importer with explicit `--apply --backup-dir`.
- [ ] Re-run it and confirm zero new inserts and stable quarantine counts.
- [ ] Reconcile users, homework, submissions, projects, files and announcements by count and sample checksum.
- [ ] Test rollback/restore before any production approval.

## Role and workflow checks

- [ ] Anonymous users cannot open a protected route.
- [ ] Student A cannot see Student B history, files, conversations, progress or submissions.
- [ ] Students cannot open teacher/admin pages or index/delete knowledge documents.
- [ ] Teachers cannot view another teacher's private course analytics/documents.
- [ ] A student enrolled in two courses with the same topic produces separate course quiz counts, mistakes and progress; unattributed old attempts appear in neither course's metrics.
- [ ] Admin-only activation/deactivation works and revokes sessions.
- [ ] Student: register/login/logout, Home, Dashboard, Courses, full Mission, quiz persistence, Tutor, homework, projects, profile and notifications.
- [ ] Teacher: dashboards, course/homework creation, submissions, announcements, projects, knowledge upload/retrieval/delete.
- [ ] Admin: account list, reset code lifecycle, deactivation/reactivation and audit visibility.

## AI/RAG checks

- [ ] Provider timeout and failover are observed with mocked/disabled primary provider.
- [ ] Provider budget/rate errors are safe and do not expose keys.
- [ ] Cross-course and private-document retrieval returns no passage.
- [ ] A malicious document containing prompt instructions does not override assistant policy.
- [ ] Citations quote the retrieved source and missing evidence triggers abstention.
- [ ] Offline hashing retrieval and optional semantic retrieval are compared on the fixed gold set.
- [ ] Document replacement/deletion leaves no stale/orphaned chunks after restart.

## Operations

- [ ] Health page reports the expected database/provider/storage mode without values.
- [ ] Structured logs contain correlation IDs and no passwords, tokens, full questions or private documents.
- [ ] Backup retention, restore owner and incident contact are documented.
- [ ] Alerting does not depend on a wasteful keep-alive ping.
- [ ] Resource/cost caps are configured for AI and storage.

## Release decision

Do not approve production use while secure browser session transport, PostgreSQL staging, RLS/object storage authorization or real-data reconciliation remains unverified.
