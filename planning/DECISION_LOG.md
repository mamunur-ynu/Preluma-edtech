# Decision log

## ADR-001 — Continue the modular Streamlit branch

Decision: use `feature/preluma-release-hardening` and preserve draft PR #2. Reason: it contains the authorized v5.1 refactor and current features; `main` is historical monolithic code. Alternative of restarting from `main` was rejected because it would discard tested work and identity assets.

## ADR-002 — Fail closed on missing RAG visibility

Decision: unlabeled stored chunks are hidden. Curated topic packs explicitly declare public visibility and are reindexed if an old index lacks the label. Reason: treating missing metadata as public could leak old uploads. Alternative of trusting old metadata was rejected. Rollback is revert of SEC-01 commit; it would reintroduce the privacy risk.

## ADR-003 — Keep production auth and staging approval gates open

Decision: maintain the modular Streamlit UI and plan a supported gateway/BFF for secure cookies. Do not claim that Streamlit client JavaScript can provide HttpOnly cookies. Local session fixes improve current revocation but do not close the external transport gate. No staging or production action has been authorized.

## ADR-004 — Revalidate a server session on every Streamlit rerun

Decision: every successful login creates an opaque, revocable server session token in the current Streamlit connection state. Each rerun resolves that token from the database and refreshes the role/name before protected views render. Browser persistence remains disabled by default and is a separate demo-only opt-in. This closes stale open-tab access after deactivation, reset or role change without pretending Streamlit has HttpOnly browser cookies. Acceptance: AppTests show revocation and role refresh; existing journeys pass. Rollback: revert this change and its helper updates if a regression is found, while keeping production use blocked because the older behavior leaves open tabs stale.

## ADR-005 — Teacher analytics roster scope and shared catalog

Decision: active teachers may view students enrolled in their published courses or the ownerless default/shared published catalog; admins may view all students. Per-course access and drill-down are checked again in services, not just filtered in selectors. Aggregate mistake counts use the same roster. This matches the existing completion-report rule and preserves shared default teaching. Limitation: quiz attempts and mastery have no course key; per-course metrics are roster-scoped, not activity-scoped. DATA-03 tracks the schema remedy. Rollback: revert SEC-04 commit if necessary, but then block teacher analytics because the older service accepted arbitrary IDs.

## ADR-006 — Database-authoritative uploaded-document recovery

Decision: the database is authoritative for document ownership and privacy metadata. On local index startup, remove uploaded vectors with no matching DB record or mismatched scope/count, repair a completed vector write whose DB count commit was interrupted, and mark missing vectors as zero-chunk rows requiring re-upload. Delete searchable vectors before committing metadata removal. Reason: this fails closed in common crash windows without storing private source bytes. Rollback: revert DATA-02, but block uploaded-document use because stale vectors could remain after interrupted deletion. Multi-worker coordination is not solved by this decision (DATA-04).

## ADR-007 — Bound local reset issuance and unify AI endpoint quota

Decision: permit at most three reset-code issuances per actor/target hour and have chat plus tutor consume one per-user local AI request quota. This closes two avoidable demo bypasses without changing offline fallback. The limiter remains process-local and is **not** a multi-worker security or spend boundary. A shared atomic limiter and pre-provider-call budget are required before staging/pilot; see `docs/RATE_LIMIT_PRODUCTION_CONTRACT.md`. Rollback: revert this guard commit if a regression is found, while keeping production use blocked.

## ADR-008 — Attribute quiz activity, never guess ambiguous history

Decision: store `course_id` and `lesson_id` on future quiz attempts, infer a course only when exactly one enrolled course contains the topic, and keep ambiguous/direct attempts unattributed. A course-launched Mission carries explicit context. Teacher course/global views use attributed attempts within accessible courses for scores, topics, mistakes and drill-down; these values are labeled quiz averages, not personal mastery. The student's global mastery model is unchanged. Migration backfills only old rows with explicit lesson IDs. Reason: current enrollment is not reliable evidence of historical course membership. Rollback: revert the schema and service changes in an isolated environment only after a backup; deployed rows with provenance would be lost on downgrade.

## ADR-009 — Authenticated encrypted source for local RAG recovery

Decision: encrypt extracted upload text with Fernet and bind its encrypted payload to the original upload digest before writing the vector index. Persist ciphertext on the knowledge-document row, then rebuild missing/tampered chunks from that source at local startup. SQLite demo keys live in a private, ignored data-dir file; PostgreSQL uploads require one explicit shared owner-managed key. Missing/wrong keys fail closed. Old rows with no ciphertext cannot be reconstructed. This does not encrypt the existing JSON vector index or solve multi-worker synchronization; both require private storage and DATA-04. Rollback must retain a DB backup and the key; dropping the ciphertext column would discard recovery material.

## ADR-010 — Shared fixed-window quotas and provider-call admission

Decision: use a database-backed atomic UPSERT counter for auth failures, reset issuance and per-user AI requests when `PRELUMA_RATE_LIMIT_BACKEND=database`; PostgreSQL defaults to this backend and rejects a memory override. Hash stored subject keys, retain denials, and prune old buckets. Every provider HTTP attempt (including model fallbacks) consumes a global hourly call quota; PostgreSQL without an explicit positive `PRELUMA_PROVIDER_CALLS_PER_HOUR` makes no live call. SQLite demos retain the old local fallback. Rationale: prevent worker-by-worker quota multiplication and accidental unlimited failover. This is **not** an IP throttle or currency/token spend guarantee; staging and owner policy remain SEC-03 gates. Rollback to local counters must be limited to a single-process demo, not production.
