"use client";

import { RotateCcw } from "lucide-react";
import { useState } from "react";

import styles from "./SecurityRetryButton.module.css";

export function SecurityRetryButton({ disabled, reviewId, onRetry }: { disabled: boolean; reviewId: string; onRetry: (id: string) => Promise<void> }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  async function retry() {
    if (disabled || submitting) return;
    setSubmitting(true); setError(undefined);
    try { await onRetry(reviewId); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not retry the Safety Agent."); }
    finally { setSubmitting(false); }
  }
  return <span className={styles.action}><button aria-label="Retry Safety Agent" disabled={disabled || submitting} onClick={() => void retry()} title="Retry Safety Agent" type="button"><RotateCcw aria-hidden="true" /></button>{error ? <small role="alert">{error}</small> : null}</span>;
}
