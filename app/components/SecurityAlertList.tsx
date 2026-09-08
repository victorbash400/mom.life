import type { SecurityReview } from "../types/security";
import { SecurityAlertRow } from "./SecurityAlertRow";
import styles from "./SecurityAlertList.module.css";

export function SecurityAlertList({ reviews, selectedId, onSelect }: { reviews: SecurityReview[]; selectedId?: string; onSelect: (id: string) => void }) {
  return <section aria-label="Security alerts" className={styles.list}>{reviews.map((review) => <SecurityAlertRow key={review.id} onSelect={() => onSelect(review.id)} review={review} selected={review.id === selectedId} />)}</section>;
}
