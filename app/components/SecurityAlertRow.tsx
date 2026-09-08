import type { SecurityReview } from "../types/security";
import styles from "./SecurityAlertRow.module.css";

export function SecurityAlertRow({ review, selected, onSelect }: { review: SecurityReview; selected: boolean; onSelect: () => void }) {
  const source = review.incoming?.sender || review.incoming?.source || "Incoming item";
  return <button aria-current={selected ? "true" : undefined} className={styles.row} data-dismissed={review.dismissed} onClick={onSelect} type="button"><span><strong>{source}</strong><time dateTime={review.created_at}>{formatTime(review.created_at)}</time></span><b>{review.summary || statusLabel(review)}</b><p>{review.reason || review.incoming?.content || "Waiting for review"}</p><small data-severity={review.severity || "working"}>{review.dismissed ? "Dismissed" : review.status === "failed" ? "Needs attention" : review.severity || statusLabel(review)}</small></button>;
}

function statusLabel(review: SecurityReview) {
  if (review.status === "queued") return "Queued";
  if (review.status === "processing") return "Security Agent working";
  return "Security review";
}

function formatTime(value: string) {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" }).format(date);
}
