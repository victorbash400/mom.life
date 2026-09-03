"use client";

import { ArrowUp, Paperclip } from "lucide-react";
import { useState } from "react";
import styles from "./AskComposer.module.css";

export function AskComposer({ disabled, onSend }: { disabled: boolean; onSend: (message: string) => void }) {
  const [value, setValue] = useState("");
  function submit() { const message = value.trim(); if (!message || disabled) return; setValue(""); onSend(message); }
  return <div className={styles.composer}><textarea aria-label="Message mom.life" disabled={disabled} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder="Message mom.life" rows={3} value={value} /><footer><button aria-label="Attach files" className={styles.attach} type="button"><Paperclip /></button><button aria-label="Send message" className={styles.send} disabled={disabled || !value.trim()} onClick={submit} type="button"><ArrowUp /></button></footer></div>;
}
