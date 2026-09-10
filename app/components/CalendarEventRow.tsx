import { MapPin } from "lucide-react";
import type { CalendarEvent } from "../types/calendar";
import styles from "./CalendarEventRow.module.css";

export function CalendarEventRow({ event }: { event: CalendarEvent }) {
  const start = new Date(event.start); const end = new Date(event.end);
  const date = start.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
  const time = event.all_day ? "All day" : start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) + " – " + end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  const content = <><time dateTime={event.start}><strong>{date}</strong><small>{time}</small></time><span><b>{event.title}</b>{event.location ? <small><MapPin aria-hidden="true" />{event.location}</small> : null}</span></>;
  return event.url ? <a className={styles.event} href={event.url} rel="noreferrer" target="_blank">{content}</a> : <article className={styles.event}>{content}</article>;
}
