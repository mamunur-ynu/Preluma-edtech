import { NextRequest } from "next/server";
import {
  authConfig, emptyResponse, errorResponse, hasValidCsrf, privateRequest,
  rejectCrossOrigin, sessionFrom, setSessionCookie,
} from "@/lib/auth-bff";

export async function POST(request: NextRequest) {
  let config;
  try { config = authConfig(); } catch { return errorResponse(503, "Authentication unavailable."); }
  if (rejectCrossOrigin(request, config.publicOrigin)) return errorResponse(403, "Origin denied.");
  const session = sessionFrom(request);
  if (!session) return errorResponse(401, "Session required.");
  if (!hasValidCsrf(request, session, config.csrfSecret)) return errorResponse(403, "CSRF denied.");
  try {
    const upstream = await privateRequest(config, "/v1/auth/rotate", "POST", session);
    if (upstream.status === 401) return errorResponse(401, "Session required.");
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
