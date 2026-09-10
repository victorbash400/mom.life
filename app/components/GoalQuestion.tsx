"use client";
import { useState } from "react";
import type { GoalQuestion as Question } from "../types/goals";
import styles from "./GoalQuestion.module.css";
export function GoalQuestion({ question, onAnswer }: { question: Question; onAnswer: (answer: string) => Promise<void> }) {
  const [answer, setAnswer] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  async function submit() { setBusy(true); try { await onAnswer(answer.trim()); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not send answer."); } finally { setBusy(false); } }
  return <form className={styles.question} onSubmit={(event) => { event.preventDefault(); void submit(); }}><strong>{question.question}</strong><textarea aria-label="Your answer" placeholder="Your answer or instructions" value={answer} onChange={(event) => setAnswer(event.target.value)} required />{error ? <p role="alert">{error}</p> : null}<div><button disabled={busy} type="submit">Send answer</button></div></form>;
}
