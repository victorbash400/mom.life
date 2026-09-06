import type { Assignment } from "../types/goals";
import styles from "./AssignmentScope.module.css";

export function AssignmentScope({ assignment }: { assignment: Assignment }) {
  return <div className={styles.scope}>
    <p>{assignment.instruction}</p>
    {assignment.skills.length ? <dl>{assignment.skills.map((skill) => <div key={skill.id}><dt>{skill.name}</dt><dd>{skill.instructions}</dd></div>)}</dl> : <p>No additional skill attached.</p>}
    <p><strong>Tools:</strong> {assignment.permitted_namespaces.length ? assignment.permitted_namespaces.join(", ") : "No connected tools assigned."}</p>
    {assignment.expected_outputs.length ? <p><strong>Done when:</strong> {assignment.expected_outputs.join("; ")}</p> : null}
  </div>;
}
