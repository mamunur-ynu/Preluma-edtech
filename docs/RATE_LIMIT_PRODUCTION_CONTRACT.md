# Rate-limit and provider-budget production contract

Status: shared database counters and provider-call caps are implemented and tested against a synthetic SQLite file. **Not validated against real PostgreSQL, gateway/IP controls or a live paid provider.**

## Current local behavior

- Login and reset-code redemption lock after five failed attempts per normalized username for five minutes. Reset-code issuance permits three actor/target requests per hour without invalidating the latest valid code on denial. Chat and tutor share one per-user AI request quota.
- SQLite demos default to in-process counters. Setting `PRELUMA_RATE_LIMIT_BACKEND=database` uses an atomic, shared fixed-window UPSERT; independent local workers and concurrent requests were tested. PostgreSQL defaults to the database backend and refuses a `memory` override.
- `PRELUMA_PROVIDER_CALLS_PER_HOUR` counts each actual provider HTTP attempt, including failover/model fallback. PostgreSQL makes no live provider calls unless a positive owner-configured limit is supplied. This is a **call-count ceiling, not a currency spend limit**.

## Required distributed behavior before staging/pilot

1. Validate the implemented shared database limiter against an isolated PostgreSQL instance with two or more real workers. Account keys are SHA-256-hashed before storage, but gateway-observed IP limits are still required so unknown usernames cannot bypass an account-only key. Do not trust an arbitrary client-supplied forwarding header.
2. The implemented database bucket cleanup removes entries older than 24 hours (or a longer configured window); validate retention and outage behavior in staging. If the shared store becomes unavailable, deny auth/reset and provider calls; do **not** silently fall back to per-worker counters. Keep in-process fallback only for explicitly single-process offline demos.
3. Add provider/token-aware currency budgeting and alerting on top of the implemented per-HTTP-call ceiling. A call count does not represent cost, especially across models with different prices. No live paid calls are needed for contract tests.
4. Avoid logging passwords, reset codes, provider keys or raw IP addresses. Record only redacted decisions and aggregate counts. Document time synchronization, cleanup, lockout support and appeal procedures.
5. Validate two or more worker instances against one isolated shared store: alternating requests must exhaust one common quota; concurrent requests must not oversubscribe; expiry, store outage, process restart and provider failover must be tested. Require an owner-approved staging endpoint and synthetic accounts. No live paid calls are needed for contract tests.

Production release remains blocked until PostgreSQL/gateway staging evidence, bucket cleanup and owner-approved spend policy exist. Synthetic local tests must not be cited as production evidence.
