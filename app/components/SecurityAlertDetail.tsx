"use client";

import { Check } from "lucide-react";
import { useState } from "react";

import type { SecurityReview } from "../types/security";
import styles from "./SecurityAlertDetail.module.css";

export function SecurityAlertDetail({ review, onDismiss, onRetry }: { review: SecurityReview; onDismiss: (id: string) => Promise<void>; onRetry: (id: string) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  async function dismiss() {
    setBusy(true); setError(undefined);
    try { await onDismiss(review.id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not dismiss the alert."); }
    finally { setBusy(false); }
  }
  async function retry() {
    setBusy(true); setError(undefined);
    try { await onRetry(review.id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not retry the safety review."); }
    finally { setBusy(false); }
  }
  return <section className={styles.detail}><header><span><strong>{review.summary || "Safety review"}</strong><small>{review.category || (review.status === "failed" ? "Could not review" : "Reviewing")}{review.severity ? ` · ${review.severity}` : ""}</small></span>{review.action === "alert" && !review.dismissed ? <button disabled={busy} onClick={() => void dismiss()} type="button"><Check aria-hidden="true" />Dismiss</button> : review.status === "failed" ? <button disabled={busy} onClick={() => void retry()} type="button">Retry</button> : null}</header><section><article><header><strong>{review.incoming?.sender || review.incoming?.source || "Incoming item"}</strong><time dateTime={review.created_at}>{formatDate(review.created_at)}</time></header>{review.reason || review.failure ? <p>{review.reason || review.failure}</p> : null}{review.incoming?.content ? <blockquote>{review.incoming.content}</blockquote> : null}{error ? <small role="alert">{error}</small> : null}</article></section></section>;
}

function formatDate(value: string) { return new Intl.DateTimeFormat(undefined, { day: "numeric", hour: "numeric", minute: "2-digit", month: "short" }).format(new Date(value)); }
