"use client";

import { RotateCcw } from "lucide-react";
import { useState } from "react";
import styles from "./IntakeRetryButton.module.css";

export function IntakeRetryButton({ disabled, itemId, onRetry }: { disabled: boolean; itemId: string; onRetry: (id: string) => Promise<void> }) {
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  async function retry() {
    if (disabled || submitting) return;
    setSubmitting(true); setError(undefined);
    try { await onRetry(itemId); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not retry the Intake Agent."); }
    finally { setSubmitting(false); }
  }
  return <span className={styles.action}><button aria-label="Retry Intake Agent" disabled={disabled || submitting} onClick={() => void retry()} title="Retry Intake Agent" type="button"><RotateCcw aria-hidden="true" /></button>{error ? <small role="alert">{error}</small> : null}</span>;
}
