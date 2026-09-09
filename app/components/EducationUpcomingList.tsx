import { CalendarDays } from "lucide-react";
import type { EducationItem } from "../types/education";
import styles from "./EducationUpcomingList.module.css";

export function EducationUpcomingList({ items }: { items: EducationItem[] }) {
  return <section className={styles.section}><header><strong>Upcoming</strong><small>{items.length}</small></header>{items.length ? <ul>{items.map((item) => <li key={`${item.title}-${item.due}`}><CalendarDays aria-hidden="true" /><span><strong>{item.title}</strong><small>{item.subject}</small></span><time>{item.due}</time></li>)}</ul> : <p>No upcoming items</p>}</section>;
}
