import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getMyLearning } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/auth-bff";
import { SignInForm, SignOutButton } from "./session-controls";

export const metadata: Metadata = { title: "My learning | Preluma" };
export const dynamic = "force-dynamic";

export default async function MyLearningPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  let learning: Awaited<ReturnType<typeof getMyLearning>> = null;
  let unavailable = false;
  if (token && token.length <= 200) {
    try {
      learning = await getMyLearning(token);
    } catch {
      unavailable = true;
    }
  }
  return (
    <section className="content-section catalog" aria-labelledby="my-learning-title">
      <div className="section-heading">
        <p className="eyebrow">YOUR PRE-CLASS WORKSPACE</p>
        <h1 id="my-learning-title">My learning</h1>
        <p>A private, read-only preview of your enrolled courses.</p>
      </div>
      {unavailable ? (
        <p className="notice" role="status">Your learning preview is temporarily unavailable.</p>
      ) : !learning ? (
        <SignInForm />
      ) : (
        <>
          <div className="session-heading">
            <p className="profile-line">Welcome, {learning.user.full_name}.</p>
            <SignOutButton />
          </div>
          {learning.courses.filter((course) => course.enrolled).length === 0 ? (
            <p className="notice">You are not enrolled in a course yet.</p>
          ) : (
            <div className="course-grid">
              {learning.courses.filter((course) => course.enrolled).map((course) => (
                <article className="course-card" key={course.id}>
                  <span className="course-level">{course.level}</span>
                  <h2>{course.title}</h2>
                  <p>{course.description}</p>
                  <span className="course-meta">
                    {course.completed_lessons} of {course.lesson_count} lessons complete
                  </span>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
