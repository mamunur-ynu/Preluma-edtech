/** Local-only BFF smoke test. Requires synthetic FastAPI + Next dev servers. */
import assert from "node:assert/strict";

const base = process.env.PRELUMA_WEB_BASE_URL;
const username = process.env.PRELUMA_TEST_USERNAME;
const password = process.env.PRELUMA_TEST_PASSWORD;
if (!base || !username || !password) throw new Error("Synthetic smoke-test settings missing.");

const loginBody = JSON.stringify({ username, password });
const post = (path, headers = {}, body) => fetch(new URL(path, base), {
  method: "POST", headers, body, redirect: "manual",
});
const origin = { Origin: base };
const json = { "Content-Type": "application/json" };

assert.equal((await post("/api/auth/login", json, loginBody)).status, 403);
assert.equal((await post("/api/auth/login", { ...json, Origin: "https://evil.example" }, loginBody)).status, 403);
assert.equal((await post("/api/auth/login", { ...json, ...origin }, "x".repeat(4097))).status, 400);
assert.equal((await post("/api/auth/login", { ...json, ...origin }, JSON.stringify({
  username, password: "incorrect",
}))).status, 401);

const login = await post("/api/auth/login", { ...json, ...origin }, loginBody);
assert.equal(login.status, 204);
assert.equal(await login.text(), "");
assert.equal(login.headers.get("cache-control"), "no-store");
const cookieHeader = login.headers.get("set-cookie") || "";
for (const flag of ["__Host-preluma_session=", "HttpOnly", "Secure", "SameSite=lax", "Path=/"])
  assert.ok(cookieHeader.toLowerCase().includes(flag.toLowerCase()), `Missing cookie flag ${flag}`);
const cookie = cookieHeader.split(";")[0];
assert.ok(cookie.length > "__Host-preluma_session=".length);

const anonymousLearning = await fetch(new URL("/my-learning", base));
assert.equal(anonymousLearning.status, 200);
assert.match(await anonymousLearning.text(), /Sign in to continue/);
const privateLearning = await fetch(new URL("/my-learning", base), { headers: { Cookie: cookie } });
assert.equal(privateLearning.status, 200);
const privateHtml = await privateLearning.text();
assert.match(privateHtml, /My learning/);
assert.match(privateHtml, /Your pre-class workspace|YOUR PRE-CLASS WORKSPACE/i);
assert.match(privateHtml, /Welcome,/);
assert.match(privateHtml, /Sign out/);
assert.doesNotMatch(privateHtml, /Sign in to continue/);
assert.ok(!privateHtml.includes(cookie.split("=")[1]), "Raw session token leaked into page HTML");

const relogin = await post("/api/auth/login", { ...json, ...origin, Cookie: cookie }, loginBody);
assert.equal(relogin.status, 204);
const currentCookie = (relogin.headers.get("set-cookie") || "").split(";")[0];
assert.notEqual(currentCookie, cookie);
assert.equal((await fetch(new URL("/api/auth/csrf", base), { headers: { Cookie: cookie } })).status, 401);
const revokedLearning = await fetch(new URL("/my-learning", base), { headers: { Cookie: cookie } });
assert.match(await revokedLearning.text(), /Sign in to continue/);

const csrfResponse = await fetch(new URL("/api/auth/csrf", base), { headers: { Cookie: currentCookie } });
assert.equal(csrfResponse.status, 200);
assert.equal(csrfResponse.headers.get("cache-control"), "no-store");
const csrf = (await csrfResponse.json()).csrf_token;
assert.match(csrf, /^[a-f0-9]{64}$/);

assert.equal((await post("/api/auth/logout", { ...origin, Cookie: currentCookie })).status, 403);
assert.equal((await post("/api/auth/logout", {
  ...origin, Cookie: currentCookie, "X-Preluma-CSRF": "0".repeat(64),
})).status, 403);
assert.equal((await post("/api/auth/rotate", {
  Origin: "https://evil.example", Cookie: currentCookie, "X-Preluma-CSRF": csrf,
})).status, 403);

const rotated = await post("/api/auth/rotate", {
  ...origin, Cookie: currentCookie, "X-Preluma-CSRF": csrf,
});
assert.equal(rotated.status, 204);
const newCookie = (rotated.headers.get("set-cookie") || "").split(";")[0];
assert.notEqual(newCookie, currentCookie);
assert.equal((await fetch(new URL("/api/auth/csrf", base), { headers: { Cookie: currentCookie } })).status, 401);
const newCsrfResponse = await fetch(new URL("/api/auth/csrf", base), { headers: { Cookie: newCookie } });
assert.equal(newCsrfResponse.status, 200);
const newCsrf = (await newCsrfResponse.json()).csrf_token;
assert.notEqual(newCsrf, csrf);

const logout = await post("/api/auth/logout", {
  ...origin, Cookie: newCookie, "X-Preluma-CSRF": newCsrf,
});
assert.equal(logout.status, 204);
assert.match(logout.headers.get("set-cookie") || "", /Max-Age=0/i);
assert.equal((await fetch(new URL("/api/auth/csrf", base), { headers: { Cookie: newCookie } })).status, 401);
process.stdout.write("Synthetic BFF login/CSRF/rotate/logout smoke: PASS\n");
