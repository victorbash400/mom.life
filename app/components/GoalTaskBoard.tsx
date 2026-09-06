import type { FamilyTask } from "../types/goals";
import styles from "./GoalTaskBoard.module.css";

export function GoalTaskBoard({ task }: { task: FamilyTask }) {
  const lines = task.assignments.flatMap((assignment) => {
    const seen = new Set<string>();
    const updates = task.activities.filter((activity) => {
      const message = activity.summary.trim();
      if (activity.kind !== "worker_update" || activity.evidence.assignment_id !== assignment.id || !message || seen.has(message)) return false;
      seen.add(message);
      return true;
    });
    const running = task.status === "active" && task.run_state === "running" && assignment.status === "running";
    return [
      { id: assignment.id, message: assignment.title, active: running && updates.length === 0 },
      ...updates.map((update, index) => ({ id: update.id, message: update.summary, active: running && index === updates.length - 1 })),
    ];
  });
  if (!lines.length) return null;
  return <ol aria-label="Task board" className={styles.board}>{lines.map((line) => <li key={line.id} data-active={line.active || undefined}>{line.message}</li>)}</ol>;
}
