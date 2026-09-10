"use client";

import { ArrowUp } from "lucide-react";
import { useState, type FormEvent } from "react";
import styles from "./CalendarComposer.module.css";

export function CalendarComposer({ busy, connected, writable, onSubmit }: { busy: boolean; connected: boolean; writable: boolean; onSubmit: (text: string) => Promise<string> }) {
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || busy || !writable) return;
    try {
      await onSubmit(text.trim());
      setText("");
      setSubmitted(true);
    } catch {
      setSubmitted(false);
    }
  }
  return <form className={styles.composer} onSubmit={(event) => void submit(event)}><input aria-label="Calendar request" disabled={!writable || busy} onChange={(event) => { setText(event.target.value); setSubmitted(false); }} placeholder={writable ? "Add dinner Friday at 7" : connected ? "Reconnect Google Calendar in Connections" : "Connect Google Calendar"} value={text} /><button aria-label="Send Calendar request" disabled={!writable || busy || !text.trim()} type="submit"><ArrowUp aria-hidden="true" /></button>{submitted ? <small>Waiting for approval in Tasks</small> : null}</form>;
}
