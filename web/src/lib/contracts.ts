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

export type CurrentUserResponse = {
  id: number;
  username: string;
  full_name: string;
  role: string;
};
