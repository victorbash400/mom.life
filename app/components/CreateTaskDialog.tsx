"use client";

import { ArrowUp, X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { TaskChildSelector } from "./TaskChildSelector";
import styles from "./CreateTaskDialog.module.css";

export function CreateTaskDialog({ initialChild = "all", open, onCancel, onSubmit }: { initialChild?: string; open: boolean; onCancel: () => void; onSubmit: (child: string, text: string) => Promise<void> }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [child, setChild] = useState("all");
  const [text, setText] = useState("");
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setChild(initialChild);
      setText("");
      setError(undefined);
      setSubmitting(false);
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [initialChild, open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(child, text.trim());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create this task.");
      setSubmitting(false);
    }
  }

  return <dialog className={styles.dialog} onCancel={onCancel} ref={ref}><form onSubmit={submit}><header><h2>New Task</h2><button aria-label="Close" onClick={onCancel} type="button"><X /></button></header><section className={styles.body}><label>Child</label><TaskChildSelector onChange={setChild} value={child} /><label htmlFor="task-copy">Task</label><div className={styles.composer}><textarea autoFocus id="task-copy" onChange={(event) => { setText(event.target.value); setError(undefined); }} placeholder="What needs to be done?" rows={5} value={text} /><button aria-label="Create task" disabled={!text.trim() || submitting} type="submit"><ArrowUp /></button></div>{error ? <p role="alert">{error}</p> : null}</section><footer><button onClick={onCancel} type="button">Cancel</button><button disabled={!text.trim() || submitting} type="submit">{submitting ? "Creating" : "Create Task"}</button></footer></form></dialog>;
}
