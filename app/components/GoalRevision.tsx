"use client";
import { useState } from "react";
import styles from "./GoalQuestion.module.css";
export function GoalRevision({ onRevise }: { onRevise: (instruction: string) => Promise<void> }) {
  const [instruction, setInstruction] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  return <form className={styles.question} onSubmit={async (event) => { event.preventDefault(); setBusy(true); try { await onRevise(instruction); setInstruction(""); setError(undefined); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not revise task."); } finally { setBusy(false); } }}><textarea aria-label="Steer this task" placeholder="Change the plan, add detail, or explain how to retry…" required value={instruction} onChange={(event) => setInstruction(event.target.value)} /><div><button disabled={busy || !instruction.trim()} type="submit">{busy ? "Updating plan…" : "Update plan"}</button></div>{error ? <p role="alert">{error}</p> : null}</form>;
}
