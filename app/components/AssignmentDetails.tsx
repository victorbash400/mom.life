import type { Assignment, GoalActivity } from "../types/goals";
import { AssignmentScope } from "./AssignmentScope";
import { AssignmentToolActivity } from "./AssignmentToolActivity";
import styles from "./AssignmentDetails.module.css";
export function AssignmentDetails({ assignment, activities }: { assignment: Assignment; activities: GoalActivity[] }) {
  return <details className={styles.assignment}><summary><span>{assignment.title}</span><small>{assignment.phase.replaceAll("_", " ")}</small></summary><AssignmentScope assignment={assignment} /><AssignmentToolActivity assignment={assignment} activities={activities} /><p>{assignment.current_step}</p>{assignment.next_step ? <p>Next: {assignment.next_step}</p> : null}{assignment.report ? <p>{assignment.report}</p> : null}{assignment.evidence.outputs?.map((output) => <p key={output.name}><strong>{output.name}</strong><br />{output.evidence}</p>)}</details>;
}
