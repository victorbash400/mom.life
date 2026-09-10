import type { SecurityReview } from "../types/security";
import { SecurityAlertDetail } from "./SecurityAlertDetail";
import { SecurityAlertList } from "./SecurityAlertList";
import { SecurityEmptyState } from "./SecurityEmptyState";
import styles from "./SecurityDashboard.module.css";

export function SecurityDashboard({ reviews, selectedId, onSelect, onDismiss, onRetry }: { reviews: SecurityReview[]; selectedId?: string; onSelect: (id: string) => void; onDismiss: (id: string) => Promise<void>; onRetry: (id: string) => Promise<void> }) {
  const selected = reviews.find((review) => review.id === selectedId) ?? reviews[0];
  return <section className={styles.dashboard} data-empty={!reviews.length}>{reviews.length ? <><SecurityAlertList onSelect={onSelect} reviews={reviews} selectedId={selected?.id} />{selected ? <SecurityAlertDetail onDismiss={onDismiss} onRetry={onRetry} review={selected} /> : null}</> : <SecurityEmptyState />}</section>;
}
