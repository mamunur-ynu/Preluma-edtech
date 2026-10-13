# Secure browser/BFF contract (design and executable API preconditions)

Current `api/app.py` is read-only and requires a private server-to-server `PRELUMA_BFF_SHARED_KEY` of at least 32 characters. It accepts `X-Preluma-Session` only together with that key, validates the existing revocable server session on each private request, and emits `Cache-Control: no-store`. It has no CORS allowance, login, mutation or browser cookie. This is **not yet** an implemented production BFF or secure gateway. The API must run on a private network with TLS between trusted services. Never place the shared key or raw session token in `NEXT_PUBLIC_*`, browser JavaScript, logs or query strings.

## Intended Next.js flow

1. Next.js server action/route handles login over HTTPS and calls a future backend auth endpoint over a private network. On success it sets only an opaque session token in a first-party `HttpOnly; Secure; SameSite=Lax; Path=/` cookie, with bounded age. No token appears in JSON/HTML. Rotate the token on login and role elevation.
2. Server components and route handlers read the cookie server-side and forward it to FastAPI using the private BFF key. On each request the backend re-resolves active account, role and revocation. Do not accept a client-supplied `user_id` as authority.
3. Every browser mutation requires same-origin `Origin` validation and a session-bound CSRF token; `GET` remains side-effect-free. Logout invalidates the backend session and clears the cookie. Password reset/deactivation revokes all sessions.
4. Protect login/reset from enumeration and abuse using the existing shared counters plus trusted gateway-observed IP quotas. The gateway must strip untrusted forwarding headers; no application code should trust arbitrary `X-Forwarded-For`.
5. Keep Streamlit's current server-session flow working until the Next.js journey passes parity tests and a rollback rehearsal. The legacy browser-token bridge stays disabled.

## Test contract

Implemented API tests: absent/mismatched BFF secret denied; missing/revoked session denied; deactivation denied; role refresh observed; two users' course-enrollment views isolated; response DTO excludes password hash; no mutating route; OpenAPI v1 response shape checked. Add BFF tests before any authenticated Next.js view: cookie flags and absence from response body, CSRF/origin rejection, rotation/revocation, replay and expired-session rejection, cross-user authorization, TLS/private-network configuration, and no secret in client bundles. Execute real browser and gateway tests on isolated staging before advancing AUTH-01.
