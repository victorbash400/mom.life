import type { EducationOverview } from "../types/education";
import styles from "./EducationSummary.module.css";

export function EducationSummary({ overview }: { overview: EducationOverview }) {
  return <section className={styles.summary}><p>{overview.summary}</p><dl><div><dt>Attendance</dt><dd>{overview.attendance}</dd></div><div><dt>Subjects</dt><dd>{overview.subjects.length || "—"}</dd></div><div><dt>Upcoming</dt><dd>{overview.upcoming.length || "—"}</dd></div></dl></section>;
}
