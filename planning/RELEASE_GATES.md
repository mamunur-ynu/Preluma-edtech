# Release gates

Current evidence supports `DEMO_READY` with synthetic/offline data. It does not support `STAGING_READY`, `PILOT_READY_FOR_APPROVAL` or `PRODUCTION_RELEASE_APPROVED`.

| Gate | Required evidence | Current state |
|---|---|---|
| Local demo | Clean install, role journeys, tests, lint, syntax, image hashes, offline behavior | Partial/ongoing: suite and role AppTests pass; continue security work |
| Isolated staging | Protected staging deploy, real PostgreSQL migration/restore, RLS/private storage deny tests, gateway sessions, shared rate limits, provider evaluation under approved budget | BLOCKED by staging/gateway access and owner-controlled resources |
| Pilot approval | Security review, privacy notice/consent, teacher acceptance, backup/rollback, support, onboarding and documented exit criteria | NOT STARTED |
| Production | Explicit owner approval after all prior gates and relevant legal/technical review | NOT AUTHORIZED |

Passing local tests cannot advance the staging gate. Keep draft PR #2 unmerged and unready until an owner reviews the evidence and blockers.
