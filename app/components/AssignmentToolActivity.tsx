import type { Assignment, GoalActivity } from "../types/goals";
import styles from "./AssignmentToolActivity.module.css";

export function AssignmentToolActivity({ assignment, activities }: { assignment: Assignment; activities: GoalActivity[] }) {
  const calls = activities.filter((item) => item.kind === "tool_started" && item.evidence.assignment_id === assignment.id);
  if (!calls.length) return null;
  return <ul aria-label="Tool activity" className={styles.activity}>{calls.map((call) => {
    const result = activities.find((item) => item.evidence.call_id === call.evidence.call_id && ["tool_result", "tool_failed"].includes(item.kind));
    const status = result?.kind === "tool_failed" ? "Failed" : result ? "Returned" : assignment.status === "running" ? "Running" : "No result recorded";
    return <li key={call.id}><span>{call.evidence.action?.plugin_id} · {call.summary}</span><small>{status}</small>{result?.kind === "tool_failed" ? <p>{result.summary}</p> : null}</li>;
  })}</ul>;
}
