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
