import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const SESSION_COOKIE = "__Host-preluma_session";

type Config = { api: URL; bffKey: string; publicOrigin: string; csrfSecret: string };

export function authConfig(): Config {
  const api = process.env.PRELUMA_API_INTERNAL_URL;
  const bffKey = process.env.PRELUMA_BFF_SHARED_KEY;
  const publicOrigin = process.env.PRELUMA_PUBLIC_ORIGIN;
  const csrfSecret = process.env.PRELUMA_CSRF_SECRET;
  if (!api || !bffKey || bffKey.length < 32 || !publicOrigin || !csrfSecret || csrfSecret.length < 32)
    throw new Error("Private authentication is not configured.");
  const apiUrl = new URL(api);
  const originUrl = new URL(publicOrigin);
  const loopback = ["localhost", "127.0.0.1", "[::1]"];
  if (originUrl.origin !== publicOrigin || originUrl.username || originUrl.password)
    throw new Error("Invalid public origin.");
  if (process.env.NODE_ENV === "production" && originUrl.protocol !== "https:")
    throw new Error("HTTPS public origin required.");
  if (originUrl.protocol !== "https:" && !(
    process.env.NODE_ENV !== "production" && originUrl.protocol === "http:" &&
    loopback.includes(originUrl.hostname)
  )) throw new Error("Public origin requires HTTPS or development loopback.");
  if (apiUrl.origin !== api || apiUrl.username || apiUrl.password) throw new Error("Invalid API origin.");
  if (apiUrl.protocol !== "https:" && !(
    process.env.NODE_ENV !== "production" && apiUrl.protocol === "http:" &&
    loopback.includes(apiUrl.hostname)
  )) throw new Error("Private API requires HTTPS or development loopback.");
  return { api: apiUrl, bffKey, publicOrigin, csrfSecret };
}

export function rejectCrossOrigin(request: NextRequest, expectedOrigin: string): boolean {
  return request.headers.get("origin") !== expectedOrigin;
}

export function csrfForSession(session: string, secret: string): string {
  return createHmac("sha256", secret).update(session).digest("hex");
}

export function hasValidCsrf(request: NextRequest, session: string, secret: string): boolean {
  const supplied = request.headers.get("x-preluma-csrf") || "";
  if (!/^[a-f0-9]{64}$/.test(supplied)) return false;
  return timingSafeEqual(Buffer.from(supplied, "hex"), Buffer.from(csrfForSession(session, secret), "hex"));
}

export function sessionFrom(request: NextRequest): string | null {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  return token && token.length <= 200 ? token : null;
}

export function errorResponse(status: number, message: string): NextResponse {
  return NextResponse.json({ error: message }, {
    status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

export function emptyResponse(status = 204): NextResponse {
  return new NextResponse(null, {
    status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

export function setSessionCookie(response: NextResponse, token: string, maxAge: number): void {
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge,
  });
}

export async function privateRequest(
  config: Config, path: string, method: "GET" | "POST", session?: string, body?: unknown,
): Promise<Response> {
  return fetch(new URL(path, config.api), {
    method,
    headers: {
      "X-Preluma-BFF-Key": config.bffKey,
      ...(session ? { "X-Preluma-Session": session } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(5000),
  });
}

export async function readSmallJson(request: NextRequest): Promise<unknown> {
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json")
    throw new Error("JSON required");
  const reader = request.body?.getReader();
  if (!reader) throw new Error("Body required");
  let size = 0;
  const chunks: Uint8Array[] = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 4096) {
      await reader.cancel();
      throw new Error("Body too large");
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
}
