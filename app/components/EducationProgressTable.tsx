import type { EducationSubject } from "../types/education";
import styles from "./EducationProgressTable.module.css";

export function EducationProgressTable({ subjects }: { subjects: EducationSubject[] }) {
  return <section className={styles.section}><header><strong>Learning</strong><small>Current</small></header>{subjects.length ? <table><thead><tr><th>Subject</th><th>Focus</th><th>Progress</th></tr></thead><tbody>{subjects.map((subject) => <tr key={subject.name}><td>{subject.name}</td><td>{subject.focus}</td><td><span data-progress={subject.progress}>{subject.progress}</span></td></tr>)}</tbody></table> : <p>No learning updates yet</p>}</section>;
}
