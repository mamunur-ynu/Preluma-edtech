# Data Migration Report and Runbook

## What was implemented

- New relational target models for homework assignments/submissions, projects/files, announcements, profile extras, import runs and quarantine rows.
- `KnowledgeDocument` provenance fields: visibility, SHA-256 and version.
- Reviewed Alembic migration `20261013_01_release_hardening.py` with upgrade and downgrade paths.
- Alembic revision `20261013_02_course_provenance.py` adds nullable quiz course provenance and backfills only attempts with an explicit lesson ID. Other historical attempts remain unattributed; current enrollment is not a valid historical substitute.
- Alembic revision `20261013_03_encrypted_document_source.py` adds nullable encrypted source bytes to knowledge-document metadata. Old rows remain null until re-upload; no plaintext source is manufactured or inferred.
- `scripts/import_legacy_data.py`: dry-run by default, explicit apply, mandatory apply backup directory, source checksums, stable legacy IDs, duplicate detection, transactional writes and quarantine reporting.
- Compatibility services keep the working legacy UI intact until migration evidence is approved.

## Identity policy

The importer first matches an exact normalized username. A full name is accepted only if exactly one current user has that normalized name. Blank, missing or duplicate-name relationships are quarantined; they are never silently assigned.

Optional creator identities may remain null and are counted separately. Personal project ownership, submissions, project-file uploaders and targeted announcement audiences require unambiguous identities.

## Reconciliation fields

The JSON report records:

- source file SHA-256 values;
- rows seen per entity;
- rows that would be inserted;
- rows actually inserted;
- existing/idempotently skipped rows;
- quarantined rows;
- unresolved optional identities;
- immutable backup directory used for apply.

## Executed validation

| Check | Result |
|---|---|
| Default is dry-run and performs no writes | PASS |
| Explicit apply requires backup directory | PASS |
| Source copies plus checksum manifest created | PASS |
| Second import inserts zero duplicates | PASS |
| Duplicate full-name identity is quarantined | PASS |
| Homework/submission relationship preserved | PASS |
| Alembic upgrade against copied v5.1 SQLite schema | PASS |
| Alembic downgrade removes new targets/columns | PASS |
| Real production CSV/Supabase import | **NOT RUN** — no approved production export |
| PostgreSQL migration | **NOT RUN** — no staging instance/credentials |
| Supabase RLS validation | **NOT RUN** — no staging project/credentials |

## Safe commands

```bash
# Copy/export real data first. Never point this at a live mutable source.
python scripts/import_legacy_data.py \
  --source-dir /safe/copied-preluma-data \
  --report /safe/reports/preluma-dry-run.json

# After human reconciliation and database backup:
alembic upgrade head
python scripts/import_legacy_data.py \
  --source-dir /safe/copied-preluma-data \
  --apply \
  --backup-dir /safe/preluma-backups \
  --report /safe/preluma-backups/preluma-applied.json
```

Re-run dry-run after apply. Expected `would_insert` for already imported records is zero or every row is reported as existing; quarantine counts must be reviewed, not discarded.

## Rollback

1. Stop writes to the staging application.
2. Retain the importer report, source manifest and quarantine table.
3. Restore the pre-migration database backup rather than attempting ad-hoc row deletion.
4. Restore private object metadata/storage from its independent backup.
5. If no migrated data must be preserved, `alembic downgrade base` reverses this release's schema additions; rehearse this only on staging.
6. Re-enable legacy reads using the unchanged compatibility adapters.

## Remaining cutover work

- Obtain an owner-approved real export and identity map.
- Add entity-specific PostgreSQL concurrency/idempotency tests against staging.
- Import question/mistake detail and profile extras using reviewed field mappings.
- Build relational read/write services for homework/projects/announcements and dual-write only during an observed transition window.
- Compare counts/checksums and user-visible samples, then cut over one entity at a time.
- Remove legacy blob/CSV adapters only in a later release after rollback is no longer required.
