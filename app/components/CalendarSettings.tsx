"use client";

import { Settings2 } from "lucide-react";
import { useState } from "react";
import type { CalendarPreferences } from "../types/calendar";
import { SettingsSwitch } from "./SettingsSwitch";
import styles from "./CalendarSettings.module.css";

const timing = [{ value: 10, label: "10 minutes" }, { value: 30, label: "30 minutes" }, { value: 60, label: "1 hour" }, { value: 1440, label: "1 day" }] as const;

export function CalendarSettings({ busy, preferences, onChange }: { busy: boolean; preferences: CalendarPreferences; onChange: (preferences: CalendarPreferences) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  function save(changes: Partial<CalendarPreferences>) { void onChange({ ...preferences, ...changes }); }
  return <div className={styles.settings}><button aria-expanded={open} aria-label="Calendar reminder settings" onClick={() => setOpen((current) => !current)} type="button"><Settings2 aria-hidden="true" /></button>{open ? <section><div className={styles.row}><span>Reminders</span><SettingsSwitch checked={preferences.enabled} label="Calendar reminders" onChange={(enabled) => save({ enabled })} /></div><label><span>Notify with</span><select aria-label="Calendar reminder method" disabled={busy || !preferences.enabled} onChange={(event) => save({ reminder_method: event.target.value as CalendarPreferences["reminder_method"] })} value={preferences.reminder_method}><option value="popup">Google Calendar</option><option value="email">Email</option></select></label><label><span>Before</span><select aria-label="Calendar reminder timing" disabled={busy || !preferences.enabled} onChange={(event) => save({ reminder_minutes: Number(event.target.value) as CalendarPreferences["reminder_minutes"] })} value={preferences.reminder_minutes}>{timing.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></section> : null}</div>;
}
