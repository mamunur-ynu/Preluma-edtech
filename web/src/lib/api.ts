import "server-only";
import type { CourseListResponse, CourseSummary, CurrentUserResponse } from "./contracts";
import { authConfig, privateRequest } from "./auth-bff";

function isCourse(value: unknown): value is CourseSummary {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.id === "number" &&
    typeof row.slug === "string" &&
    typeof row.title === "string" &&
    typeof row.description === "string" &&
    typeof row.level === "string" &&
    typeof row.lesson_count === "number" &&
    typeof row.enrolled === "boolean" &&
    typeof row.completed_lessons === "number" &&
    typeof row.percent === "number"
  );
}

function isCurrentUser(value: unknown): value is CurrentUserResponse {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return typeof row.id === "number" && typeof row.username === "string" &&
    typeof row.full_name === "string" && typeof row.role === "string";
}

export async function getMyLearning(session: string): Promise<{
  user: CurrentUserResponse;
  courses: CourseSummary[];
} | null> {
  const config = authConfig();
  const [userResponse, coursesResponse] = await Promise.all([
    privateRequest(config, "/v1/me", "GET", session),
    privateRequest(config, "/v1/me/courses", "GET", session),
  ]);
  if (userResponse.status === 401 || coursesResponse.status === 401) return null;
  if (!userResponse.ok || !coursesResponse.ok) throw new Error("Learning workspace unavailable.");
  const user: unknown = await userResponse.json();
  const payload: unknown = await coursesResponse.json();
  if (!isCurrentUser(user) || typeof payload !== "object" || payload === null ||
      !Array.isArray((payload as CourseListResponse).courses) ||
      !(payload as CourseListResponse).courses.every(isCourse))
    throw new Error("Private learning contract mismatch.");
  return { user, courses: (payload as CourseListResponse).courses };
}

export async function getCatalog(): Promise<CourseSummary[]> {
  const base = process.env.PRELUMA_API_INTERNAL_URL;
  const key = process.env.PRELUMA_BFF_SHARED_KEY;
  if (!base || !key || key.length < 32)
    throw new Error("Private API connection is not configured.");
  const response = await fetch(new URL("/v1/catalog/courses", base), {
    headers: { "X-Preluma-BFF-Key": key },
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("Catalog is temporarily unavailable.");
  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !Array.isArray((payload as CourseListResponse).courses) ||
    !(payload as CourseListResponse).courses.every(isCourse)
  ) {
    throw new Error("Catalog contract mismatch.");
  }
  return (payload as CourseListResponse).courses;
}
