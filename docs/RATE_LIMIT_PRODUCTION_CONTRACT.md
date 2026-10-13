# Rate-limit and provider-budget production contract

Status: design and local safeguards only. **Not validated or enabled as a distributed control.**

## Current local behavior

- Login and reset-code redemption lock after five failed attempts per normalized username for five minutes. These counters are process-local.
- Reset-code issuance is now limited to three successful issuances per actor/target pair per hour. An over-limit request does not invalidate the most recent code. This counter is process-local.
- AI chat and tutor share the configured `PRELUMA_AI_REQUESTS_PER_MINUTE` limit per user, rather than each endpoint having a separate allowance. The counter is process-local. A provider failover can still make several external calls per allowed user request.

## Required distributed behavior before staging/pilot

1. Put login, reset issuance/redemption and AI request admission behind a shared, atomic limiter used by every web worker. Normalize and hash account keys before storage; combine account and gateway-observed IP limits so unknown usernames cannot bypass an account-only key. Do not trust an arbitrary client-supplied forwarding header.
2. Use a server-side shared store with atomic expiry and a bounded TTL. If it becomes unavailable, deny auth/reset and paid-provider calls; do **not** silently fall back to per-worker counters in a multi-worker deployment. Keep the in-process fallback only for explicitly single-process offline demos.
3. Enforce provider-level call and token budgets **before each failover attempt**, including retry paths, with a fixed owner-approved maximum spend and alerting. Disable live providers when the budget is exhausted. A per-user request limit alone does not cap provider spend.
4. Avoid logging passwords, reset codes, provider keys or raw IP addresses. Record only redacted decisions and aggregate counts. Document time synchronization, cleanup, lockout support and appeal procedures.
5. Validate two or more worker instances against one isolated shared store: alternating requests must exhaust one common quota; concurrent requests must not oversubscribe; expiry, store outage, process restart and provider failover must be tested. Require an owner-approved staging endpoint and synthetic accounts. No live paid calls are needed for contract tests.

Production release remains blocked until that shared implementation and its staging evidence exist. Current local tests must not be cited as proof of distributed protection.
