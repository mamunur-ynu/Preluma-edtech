# Preluma v5.1 Release-Hardening Architecture

## Layer contract

```text
app.py + views/ + components/        Streamlit presentation and server-owned UI session state
                 │
                 ▼
services/                            use cases, authorization, compatibility adapters
        ┌────────┼──────────┐
        ▼        ▼          ▼
auth/       core/ + ai/    database/ + security/
identity    pure learning   repositories, models,
sessions    algorithms      migrations, validation
```

Enforced rules:

- `auth/`, `ai/`, `core/`, `database/`, `services/` and `security/` do not import Streamlit.
- `core/` remains standard-library-only; the course-required merge sort, search, mean and variance implementations are preserved.
- Views call services rather than importing database, CSV storage or project/homework persistence modules directly.
- Repositories own queries but not commits; service/session scopes own transactions.
- Services return plain dataclasses/dictionaries, not live ORM objects.

The app shell may initialise the database and route authenticated users. It must not contain provider HTTP calls or domain persistence logic.

## Runtime entry points

- `streamlit_app.py`: deployment-compatible thin entry point
- `app.py`: Streamlit page configuration, bootstrap, sidebar, role guard and route dispatch
- `scripts/create_user.py`: controlled local account creation
- `scripts/seed_demo.py`: explicitly synthetic demo data
- `scripts/import_legacy_data.py`: dry-run-first legacy migration utility
- `alembic.ini` + `migrations/`: controlled relational schema evolution

## Domain modules

| Area | Modules | Responsibility |
|---|---|---|
| Authentication | `auth/` | PBKDF2 passwords, legacy hash upgrade, registration, reset lifecycle, opaque sessions |
| Services | `services/` | user/course/learning/analytics/AI use cases and legacy compatibility boundaries |
| Learning core | `core/` | assessment, recommendations, mastery, knowledge graph, algorithms, topic packs |
| AI/RAG | `ai/` | provider router, embeddings, vector store, chunking, retrieval, prompt and memory policy |
| Relational data | `database/` | SQLAlchemy models, repositories, transactions and migration targets |
| Security | `security/` | upload validation and in-process abuse control |
| Presentation | `views/`, `components/` | role-specific pages, reusable cards/charts/theme, controlled HTML escaping |

## Relational model

The current schema contains users, sessions, resets, courses, lessons, enrolments, progress, quiz attempts/mistakes, skill profiles, recommendations, achievements, conversation history and knowledge-document metadata.

Release hardening adds relational targets for:

- homework assignments and submissions;
- class/personal projects and private project-file metadata;
- announcements;
- user profile extras and avatar object keys;
- legacy import runs and quarantine rows.

The legacy UI remains behind `services.homework_service`, `services.project_service`, `services.mission_history_service` and `services.audit_service` until real data has been dry-run, reconciled and approved. This compatibility layer is deliberate: relational tables existing is not treated as proof that production data has migrated.

## Identity and authorization

1. A password is verified against a salted PBKDF2 hash. Legacy unsalted SHA-256 is accepted only to enable a transparent rehash on successful login.
2. A server-side session row stores only a SHA-256 token hash, expiry and revocation state.
3. Role and active state are re-read from the user table when a server token resolves.
4. Streamlit session state is populated from the authenticated `AuthUser`; role-only navigation is supplemented by service-level checks.
5. Reset/admin operations accept a validated actor ID. Teachers may reset students; admins may reset staff. Issuing a new reset code invalidates older unused codes.
6. Deactivation revokes every active user session.

Streamlit cannot issue a secure first-party HttpOnly authentication cookie. Persistent browser restore is therefore disabled unless the deployer explicitly enables the legacy demo bridge. Production must put authentication behind a secure gateway/FastAPI transport.

## RAG data flow and trust boundary

```text
teacher upload
  → content-aware validation
  → document metadata + SHA-256 + visibility
  → chunk/embed/index
  → visibility filter (public/private/staff/course)
  → hybrid rank
  → untrusted source blocks
  → LLM or extractive offline answer
  → citation metadata stored with user-scoped conversation
```

The visibility filter is applied before a passage is returned. Course material cannot be treated as system instructions. Prompt construction labels retrieved blocks as untrusted and asks the model to ignore role changes, secret requests and commands inside them. Conversation history is scoped by both `user_id` and `session_id`, clearable, and retention-limited.

The built-in hashing embedder is deterministic and cheap but lexical. Optional semantic embeddings and FAISS remain configurable rather than mandatory, preserving Streamlit Cloud resource viability.

## Upload model

- Filenames are reduced to a safe basename.
- Extension, byte limit and common file signatures must agree.
- Empty, oversized and binary-NUL text uploads are rejected.
- Private local compatibility uploads are content-addressed and written atomically.
- Project file limit: 25 MB; knowledge documents: 10 MB; profile images: 5 MB.
- Production must use private object storage, short-lived signed downloads, malware quarantine and server-side authorization; the local/Supabase blob compatibility path is not the production target.

## Data migration workflow

1. Copy—not move—the production CSV export into an isolated source directory.
2. Back up database and object storage.
3. Run `scripts/import_legacy_data.py` without `--apply`.
4. Reconcile source hashes, rows seen, would-insert, existing, unresolved and quarantine counts.
5. Resolve ambiguous identities using a human-reviewed username/ID map; never guess from duplicate full names.
6. Run the Alembic migration on staging.
7. Run the importer with explicit `--apply --backup-dir ...`.
8. Re-run dry-run; expected new inserts are zero.
9. Exercise student/teacher/admin workflows and compare counts/checksums.
10. Cut reads over entity-by-entity with rollback available. Remove legacy adapters only in a later reviewed release.

## Concurrency and deployment

- SQLite uses foreign keys and WAL and is suitable only for disposable local/demo mode.
- PostgreSQL is the persistent staging/production target.
- SQL writes use transactional session scopes and database uniqueness constraints.
- The in-process AI limiter protects a single process. Multi-worker deployments require a shared limiter at the gateway.
- Vector JSON persistence is atomic but process-local; production-scale indexing needs a durable vector/object service or coordinated job worker.

## Quality gates

- Ruff across the full tree
- Python compilation
- Pytest unit/integration/UI/negative authorization/migration tests
- Streamlit AppTest and actual browser role/viewport inspection
- Bandit static scan (B311 excluded only for non-security educational/demo randomisation)
- `pip-audit` dependency scan
- Alembic upgrade/downgrade against a copied v5.1 SQLite baseline
- Asset hash and final ZIP secret/runtime-data scans

Actual results are in `reports/BASELINE.md` and `reports/FINAL_VERIFICATION.md`.

## Known architecture blockers

- Legacy homework/project/announcement/profile reads have not been cut over to relational repositories because no real production export was supplied for reconciliation.
- Streamlit persistent authentication lacks a secure cookie transport.
- PostgreSQL/RLS and multi-process concurrency were not tested against a live staging instance.
- Supabase legacy blob tables require owner-reviewed RLS and should not use an anonymous broad policy.

See `docs/FUTURE_FASTAPI_NEXTJS_MIGRATION.md` for the incremental transport contract.
