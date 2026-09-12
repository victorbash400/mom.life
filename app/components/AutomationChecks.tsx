import { useEffect, useState } from "react";
import type { FamilyTask } from "../types/goals";
import { AssignmentDetails } from "./AssignmentDetails";
import { GoalQuestion } from "./GoalQuestion";
import { subscribeFamilyEvents } from "../lib/familyEvents";
import styles from "./AutomationList.module.css";
type Check = { id: string; state: string; created_at: string; failure: string; task: FamilyTask | null };
export function AutomationChecks({ automationId }: { automationId: string }) {
  const [checks, setChecks] = useState<Check[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    async function refresh() {
      try {
        const response = await fetch(`/api/automations/${automationId}/runs`, { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Could not load checks.");
        if (live) { setChecks(payload); setError(""); }
      } catch (cause) { if (live) setError(cause instanceof Error ? cause.message : "Could not load checks."); }
    }
    void refresh();
    const unsubscribe = subscribeFamilyEvents({ onEvent: (event) => { if (event.type === "goals_changed" || event.type === "automations_changed") void refresh(); }, onConnection: (connected) => { if (connected) void refresh(); } });
    return () => { live = false; unsubscribe(); };
  }, [automationId]);
  async function answer(taskId: string, questionId: string, answer: string) {
    const response = await fetch(`/api/tasks/${taskId}/questions/${questionId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer }) });
    if (!response.ok) { const payload = await response.json(); throw new Error(payload.error || "Could not answer this check."); }
  }
  return <div className={styles.checks}>{error && <p role="alert">{error}</p>}{checks.map((check) => <details key={check.id}><summary>{new Date(check.created_at).toLocaleString()} · {check.task?.run_state ?? check.state}</summary>{check.failure && <p role="alert">{check.failure}</p>}{check.task?.report && <p>{check.task.report}</p>}{check.task?.assignments.map((assignment) => <AssignmentDetails key={assignment.id} assignment={assignment} activities={check.task!.activities} />)}{check.task?.questions.filter((question) => question.state === "open").map((question) => <GoalQuestion key={question.id} question={question} onAnswer={(value) => answer(check.task!.id, question.id, value)} />)}</details>)}</div>;
}
