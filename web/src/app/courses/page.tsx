import type { Metadata } from "next";
import { getCatalog } from "@/lib/api";

export const metadata: Metadata = { title: "Courses | Preluma" };
export const dynamic = "force-dynamic";

export default async function CoursesPage() {
  let courses: Awaited<ReturnType<typeof getCatalog>> = [];
  let unavailable = false;
  try {
    courses = await getCatalog();
  } catch {
    unavailable = true;
  }
  return (
    <section
      className="content-section catalog"
      aria-labelledby="courses-title"
    >
      <div className="section-heading">
        <p className="eyebrow">PREPARE WITH PURPOSE</p>
        <h1 id="courses-title">Course library</h1>
        <p>Explore the published pre-class learning paths.</p>
      </div>
      {unavailable ? (
        <p className="notice" role="status">
          The course catalog is temporarily unavailable. Your existing Streamlit
          learning workspace is unaffected.
        </p>
      ) : courses.length === 0 ? (
        <p className="notice">No courses have been published yet.</p>
      ) : (
        <div className="course-grid">
          {courses.map((course) => (
            <article className="course-card" key={course.id}>
              <span className="course-level">{course.level}</span>
              <h2>{course.title}</h2>
              <p>{course.description}</p>
              <span className="course-meta">{course.lesson_count} lessons</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
