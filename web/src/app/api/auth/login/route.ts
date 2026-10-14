import { NextRequest } from "next/server";
import {
  authConfig, emptyResponse, errorResponse, privateRequest, readSmallJson,
  rejectCrossOrigin, sessionFrom, setSessionCookie,
} from "@/lib/auth-bff";

export async function POST(request: NextRequest) {
  let config;
  try { config = authConfig(); } catch { return errorResponse(503, "Authentication unavailable."); }
  if (rejectCrossOrigin(request, config.publicOrigin)) return errorResponse(403, "Origin denied.");
  let body: unknown;
  try { body = await readSmallJson(request); } catch { return errorResponse(400, "Invalid request."); }
  if (typeof body !== "object" || body === null) return errorResponse(400, "Invalid request.");
  const { username, password } = body as Record<string, unknown>;
  if (typeof username !== "string" || username.length < 1 || username.length > 32 ||
      typeof password !== "string" || password.length < 1 || password.length > 512)
    return errorResponse(400, "Invalid request.");
  try {
    const upstream = await privateRequest(
      config, "/v1/auth/login", "POST", sessionFrom(request) || undefined, { username, password },
    );
    if (upstream.status === 401) return errorResponse(401, "Invalid credentials.");
    if (!upstream.ok) return errorResponse(503, "Authentication unavailable.");
    const data: unknown = await upstream.json();
    if (typeof data !== "object" || data === null) throw new Error("Contract mismatch");
    const { session_token: token, expires_in_seconds: maxAge } = data as Record<string, unknown>;
    if (typeof token !== "string" || !token || token.length > 200 ||
        typeof maxAge !== "number" || !Number.isInteger(maxAge) || maxAge < 1 || maxAge > 2592000)
      throw new Error("Contract mismatch");
    const response = emptyResponse();
    setSessionCookie(response, token, maxAge);
    return response;
  } catch { return errorResponse(503, "Authentication unavailable."); }
}
