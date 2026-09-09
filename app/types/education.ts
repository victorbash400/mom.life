export type EducationProgress = "Strong" | "On track" | "Needs attention";
export type EducationSubject = { name: string; focus: string; progress: EducationProgress };
export type EducationItem = { title: string; subject: string; due: string };
export type EducationOverview = { summary: string; attendance: string; subjects: EducationSubject[]; upcoming: EducationItem[] };
