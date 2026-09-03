"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import styles from "./CreateTaskDialog.module.css";
export function CreateTaskDialog({ open, onCancel, onSubmit }: { open: boolean; onCancel: () => void; onSubmit: (child: string, text: string) => Promise<void> }) {
  const ref = useRef<HTMLDialogElement>(null); const [child, setChild] = useState("all"); const [text, setText] = useState(""); const [error, setError] = useState<string>();
  useEffect(() => { const dialog = ref.current; if (!dialog) return; if (open && !dialog.open) { setChild("all"); setText(""); setError(undefined); dialog.showModal(); } else if (!open && dialog.open) dialog.close(); }, [open]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!text.trim()) return; try { await onSubmit(child, text.trim()); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create this task."); } }
  return <dialog className={styles.dialog} onCancel={onCancel} ref={ref}><form onSubmit={submit}><h2>New Task</h2><section><label>Child<select onChange={(event) => setChild(event.target.value)} value={child}><option value="all">All Children</option><option value="amina">Amina</option><option value="noah">Noah</option><option value="lila">Lila</option></select></label><label>Task<textarea autoFocus onChange={(event) => setText(event.target.value)} placeholder="What should mom.life accomplish?" rows={6} value={text} /></label>{error ? <p role="alert">{error}</p> : null}</section><footer><button onClick={onCancel} type="button">Cancel</button><button disabled={!text.trim()} type="submit">Create and Start</button></footer></form></dialog>;
}
