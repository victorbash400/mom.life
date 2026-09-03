"use client";

import { Camera, ChevronDown, Plug } from "lucide-react";
import { useState } from "react";
import type { ChildProfile } from "../types/dashboard";
import { SettingsRow } from "./SettingsRow";
import { SettingsSwitch } from "./SettingsSwitch";
import styles from "./ChildSettingsDisclosure.module.css";

export function ChildSettingsDisclosure({ child }: { child: ChildProfile }) {
  const [email, setEmail] = useState(true);
  const [text, setText] = useState(false);
  const [notifications, setNotifications] = useState(true);
  return <details className={styles.child}><summary><i style={{ backgroundPosition: child.avatarPosition }} /><span><strong>{child.name}</strong><small>{child.age}</small></span><ChevronDown /></summary><section><SettingsRow control={<button className={styles.photo} type="button"><Camera />Upload</button>} description="Change this child's profile picture" title="Profile photo" /><SettingsRow control={<span className={styles.methods}><button aria-pressed={email} onClick={() => setEmail((value) => !value)} type="button">Email</button><button aria-pressed={text} onClick={() => setText((value) => !value)} type="button">Text</button></span>} description="Choose how Sarah receives updates" title="Updates through" /><SettingsRow control={<SettingsSwitch checked={notifications} label={`${child.name} notifications`} onChange={setNotifications} />} description="Health, school, task, and activity changes" title="Notifications" /><SettingsRow control={<button className={styles.connect} type="button"><Plug />Connect</button>} description="Calendars, school portals, health, and other tools" title="Connectors" /></section></details>;
}
