"use client";

import { Check, CircleAlert, LoaderCircle, X } from "lucide-react";
import { useEffect, useRef } from "react";

import type { SecurityReview } from "../types/security";
import { SecurityRetryButton } from "./SecurityRetryButton";
import styles from "./SecurityAgentActivity.module.css";

export function SecurityAgentActivity({ review, onRetry }: { review: SecurityReview; onRetry: (id: string) => Promise<void> }) {
  const running = review.status === "processing" || review.status === "queued";
  const activityRef = useRef<HTMLElement>(null);
  useEffect(() => {
    activityRef.current?.scrollTo({ behavior: "smooth", top: activityRef.current.scrollHeight });
  }, [review.activities.length, review.status]);
  return <aside aria-label="Safety Agent activity" className={styles.activity} ref={activityRef}><header><strong>Safety Agent</strong><span className={styles.controls}><Status status={review.status} /><SecurityRetryButton disabled={running} onRetry={onRetry} reviewId={review.id} /></span></header>{review.failure ? <p className={styles.failure}><CircleAlert aria-hidden="true" />{review.failure}</p> : null}<ol>{review.activities.map((activity, index) => { const current = running && index === review.activities.length - 1; const failed = review.status === "failed" && index === review.activities.length - 1; return <li data-state={failed ? "failed" : current ? "running" : "completed"} key={activity.id}><span className={styles.marker}>{failed ? <X aria-hidden="true" /> : current ? <LoaderCircle aria-hidden="true" /> : <Check aria-hidden="true" />}</span><span className={styles.step}>{safetyCopy(activity.summary)}</span></li>; })}</ol></aside>;
}

function safetyCopy(value: string) { return value.replaceAll("Security Agent", "Safety Agent").replaceAll("Security monitoring", "Safety monitoring"); }

function Status({ status }: { status: SecurityReview["status"] }) {
  if (status === "processing" || status === "queued") return <small className={styles.running}><LoaderCircle aria-hidden="true" />{status === "queued" ? "Queued" : "Working"}</small>;
  return <small>{status === "failed" ? "Needs attention" : "Done"}</small>;
}
