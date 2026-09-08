import type { IncomingItem } from "../types/intake";
import styles from "./IntakeDetail.module.css";

export function IntakeDetail({ item }: { item: IncomingItem }) {
  return <section className={styles.detail}><header><strong>{item.subject || item.source}</strong><small>{item.sender || "Unknown sender"} · {item.source}</small></header><section><article><header><strong>{item.sender || item.source}</strong><time dateTime={item.created_at}>{formatDate(item.created_at)}</time></header><p>{item.content}</p></article></section></section>;
}

function formatDate(value: string) { return new Intl.DateTimeFormat(undefined, { day: "numeric", hour: "numeric", minute: "2-digit", month: "short" }).format(new Date(value)); }
