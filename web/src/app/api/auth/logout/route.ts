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
    const upstream = await privateRequest(config, "/v1/auth/logout", "POST", session);
    if (!upstream.ok) return errorResponse(503, "Authentication unavailable.");
    const response = emptyResponse();
    setSessionCookie(response, "", 0);
    return response;
  } catch { return errorResponse(503, "Authentication unavailable."); }
}
