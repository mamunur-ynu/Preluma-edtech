import { NextRequest, NextResponse } from "next/server";
import { authConfig, csrfForSession, errorResponse, privateRequest, sessionFrom } from "@/lib/auth-bff";

export async function GET(request: NextRequest) {
  let config;
  try { config = authConfig(); } catch { return errorResponse(503, "Authentication unavailable."); }
  const session = sessionFrom(request);
  if (!session) return errorResponse(401, "Session required.");
  try {
    const upstream = await privateRequest(config, "/v1/me", "GET", session);
    if (upstream.status === 401) return errorResponse(401, "Session required.");
    if (!upstream.ok) return errorResponse(503, "Authentication unavailable.");
    return NextResponse.json({ csrf_token: csrfForSession(session, config.csrfSecret) }, {
      headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
    });
  } catch { return errorResponse(503, "Authentication unavailable."); }
}
