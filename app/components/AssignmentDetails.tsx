import type { Assignment } from "../types/goals";
import styles from "./AssignmentDetails.module.css";
export function AssignmentDetails({ assignment }: { assignment: Assignment }) {
  return <details className={styles.assignment}><summary><span>{assignment.title}</span><small>{assignment.phase.replaceAll("_", " ")}</small></summary><p>{assignment.current_step}</p>{assignment.next_step ? <p>Next: {assignment.next_step}</p> : null}{assignment.report ? <p>{assignment.report}</p> : null}{assignment.evidence.outputs?.map((output) => <p key={output.name}><strong>{output.name}</strong><br />{output.evidence}</p>)}</details>;
}
