"use client";
import { useState } from "react";
import type { GoalQuestion as Question } from "../types/goals";
import styles from "./GoalQuestion.module.css";
export function GoalQuestion({ question, onAnswer }: { question: Question; onAnswer: (answer: string, approved: boolean) => Promise<void> }) {
  const [answer, setAnswer] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  async function submit(approved: boolean) { setBusy(true); try { await onAnswer(answer.trim() || (approved ? "Approved this exact action." : "Do not perform this action."), approved); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not send answer."); } finally { setBusy(false); } }
  return <form className={styles.question} onSubmit={(event) => { event.preventDefault(); void submit(false); }}><strong>{question.question}</strong>{question.context ? <p>{question.context}</p> : null}{question.action ? <pre>{JSON.stringify(question.action.arguments, null, 2)}</pre> : null}<textarea aria-label="Your answer" placeholder="Your answer or instructions" value={answer} onChange={(event) => setAnswer(event.target.value)} required={!question.action} />{error ? <p role="alert">{error}</p> : null}<div>{question.action ? <button disabled={busy} onClick={() => void submit(true)} type="button">Approve this action</button> : null}<button disabled={busy} type="submit">{question.action ? "Decline / send instructions" : "Send answer"}</button></div></form>;
}
