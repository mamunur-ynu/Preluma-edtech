# Rate-limit and provider-budget production contract

Status: shared database counters, provider-call caps and owner-priced estimated-cost reservations are implemented and tested against synthetic SQLite. **Not validated against real PostgreSQL, gateway/IP controls or a live paid provider.**

## Current local behavior

- Login and reset-code redemption lock after five failed attempts per normalized username for five minutes. Reset-code issuance permits three actor/target requests per hour without invalidating the latest valid code on denial. Chat and tutor share one per-user AI request quota.
- SQLite demos default to in-process counters. Setting `PRELUMA_RATE_LIMIT_BACKEND=database` uses an atomic, shared fixed-window UPSERT; independent local workers and concurrent requests were tested. PostgreSQL defaults to the database backend and refuses a `memory` override.
- `PRELUMA_PROVIDER_CALLS_PER_HOUR` admits each provider HTTP attempt, including failover/model fallback. PostgreSQL makes no live call unless a positive owner-configured limit is supplied.
- `PRELUMA_PROVIDER_MAX_USD_PER_DAY` and `PRELUMA_PROVIDER_PRICES_JSON` reserve an estimated cost in shared cents before an attempt. The JSON keys are exact `provider:model` strings, each with positive `input_usd_per_million` and `output_usd_per_million` values supplied/reviewed by the owner. The estimate uses UTF-8 request bytes plus overhead and the requested maximum output tokens, rounded *up* to at least one cent. A missing price or limit fails closed on PostgreSQL. SQLite demos without either setting retain offline/demo behavior. This is conservative admission control, **not a guaranteed provider-billed currency ceiling**: hidden tokens, provider-side pricing changes, rounding and unsuccessful reservations can differ from actual invoices.

## Required distributed behavior before staging/pilot

1. Validate the implemented shared database limiter against an isolated PostgreSQL instance with two or more real workers. Account keys are SHA-256-hashed before storage, but gateway-observed IP limits are still required so unknown usernames cannot bypass an account-only key. Do not trust an arbitrary client-supplied forwarding header.
2. The implemented database bucket cleanup removes entries older than 24 hours (or a longer configured window); validate retention and outage behavior in staging. If the shared store becomes unavailable, deny auth/reset and provider calls; do **not** silently fall back to per-worker counters. Keep in-process fallback only for explicitly single-process offline demos.
3. Validate the owner-supplied price table against current provider contracts, reconcile actual usage/billing, configure provider-side hard spending limits and alerts, and verify failover/model-price behavior on staging under an approved budget. The local reservation is deliberately not called an invoice-accurate hard cap. No live paid calls are needed for contract tests.
4. Avoid logging passwords, reset codes, provider keys or raw IP addresses. Record only redacted decisions and aggregate counts. Document time synchronization, cleanup, lockout support and appeal procedures.
5. Validate two or more worker instances against one isolated shared store: alternating requests must exhaust one common quota; concurrent requests must not oversubscribe; expiry, store outage, process restart and provider failover must be tested. Require an owner-approved staging endpoint and synthetic accounts. No live paid calls are needed for contract tests.

Production release remains blocked until PostgreSQL/gateway staging evidence, bucket cleanup and owner-approved spend policy exist. Synthetic local tests must not be cited as production evidence.
