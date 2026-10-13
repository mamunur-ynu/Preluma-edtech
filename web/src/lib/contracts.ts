export type CourseSummary = {
  id: number;
  slug: string;
  title: string;
  description: string;
  level: string;
  lesson_count: number;
  enrolled: boolean;
  completed_lessons: number;
  percent: number;
};

export type CourseListResponse = { courses: CourseSummary[] };
