import { useCalendar } from "../hooks/useCalendar";
import { CalendarComposer } from "./CalendarComposer";
import { CalendarEventRow } from "./CalendarEventRow";
import { CalendarSettings } from "./CalendarSettings";
import { LoadingIndicator } from "./LoadingIndicator";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./CalendarWorkspace.module.css";

export function CalendarWorkspace({ onClose }: { onClose: () => void }) {
  const calendar = useCalendar();
  return <section className={styles.workspace}><WorkspaceHeader title="Calendar" onClose={onClose} action={<CalendarSettings busy={calendar.busy} onChange={calendar.savePreferences} preferences={calendar.preferences} />} />{calendar.error ? <p className={styles.error} role="alert">{calendar.error}</p> : null}<div className={styles.body}><section className={styles.events} aria-label="Upcoming events">{calendar.loaded ? calendar.events.length ? calendar.events.map((event) => <CalendarEventRow event={event} key={event.id} />) : <p>{calendar.connected ? "No upcoming events" : "Connect Google Calendar in Connections"}</p> : !calendar.error ? <LoadingIndicator /> : null}</section><CalendarComposer busy={calendar.busy} connected={calendar.connected} onSubmit={calendar.request} writable={calendar.writable} /></div></section>;
}
