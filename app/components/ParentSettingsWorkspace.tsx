"use client";
import { ChildEditor } from "./ChildEditor";
import Image from "next/image";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useFamily } from "./FamilyProvider";
import { SettingsRow } from "./SettingsRow";
import { SettingsSwitch } from "./SettingsSwitch";
import { ChildSettingsDisclosure } from "./ChildSettingsDisclosure";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./ParentSettingsWorkspace.module.css";

export type ParentSettingsView = "profile" | "children";
export function ParentSettingsWorkspace({ initialView = "profile", onBack }: { initialView?: ParentSettingsView; onBack: () => void }) {
  const { family: { parent } } = useFamily();
  const [view, setView] = useState<ParentSettingsView>(initialView);
  const [appointments, setAppointments] = useState(true);
  const [taskUpdates, setTaskUpdates] = useState(true);
  const [weeklySummary, setWeeklySummary] = useState(false);
  const [childUpdates, setChildUpdates] = useState(true);
  return <section className={styles.workspace}><header className={styles.header}><WorkspaceHeader backLabel={`Back to ${parent.name}`} title="Settings" onClose={onBack} /><nav aria-label="Settings section"><button aria-pressed={view === "profile"} onClick={() => setView("profile")} type="button">Profile</button><button aria-pressed={view === "children"} onClick={() => setView("children")} type="button">Child Management</button></nav></header><div className={styles.scroll}>{view === "profile" ? <ProfileSettings appointments={appointments} onAppointments={setAppointments} onTaskUpdates={setTaskUpdates} onWeeklySummary={setWeeklySummary} taskUpdates={taskUpdates} weeklySummary={weeklySummary} /> : <ChildSettings childUpdates={childUpdates} onChildUpdates={setChildUpdates} />}</div></section>;
}

function ProfileSettings({ appointments, taskUpdates, weeklySummary, onAppointments, onTaskUpdates, onWeeklySummary }: { appointments: boolean; taskUpdates: boolean; weeklySummary: boolean; onAppointments: (value: boolean) => void; onTaskUpdates: (value: boolean) => void; onWeeklySummary: (value: boolean) => void }) {
  const { family: { parent } } = useFamily();
  return <><SettingsSection title="Profile"><SettingsRow control={<span className={styles.identity}><Image alt={parent.name} height={38} src="/sarah-profile.png" width={38} /><span>{parent.name}</span></span>} description="Your personal details and family role" title="Personal profile" /><SettingsRow control={<button className={styles.value} type="button">Parent</button>} title="Family role" /></SettingsSection><SettingsSection title="Notifications"><SettingsRow control={<SettingsSwitch checked={appointments} label="Appointment reminders" onChange={onAppointments} />} description="Upcoming health and school appointments" title="Appointment reminders" /><SettingsRow control={<SettingsSwitch checked={taskUpdates} label="Task updates" onChange={onTaskUpdates} />} description="Changes to family tasks" title="Task updates" /><SettingsRow control={<SettingsSwitch checked={weeklySummary} label="Weekly family summary" onChange={onWeeklySummary} />} description="A weekly overview of family activity" title="Weekly family summary" /></SettingsSection><SettingsSection title="Preferences"><SettingsRow control={<button className={styles.value} type="button">English</button>} title="Language" /><SettingsRow control={<button className={styles.value} type="button">Nairobi</button>} title="Time zone" /></SettingsSection></>;
}

function ChildSettings({ childUpdates, onChildUpdates }: { childUpdates: boolean; onChildUpdates: (value: boolean) => void }) {
  const { family: { children } } = useFamily();
  const [adding, setAdding] = useState(false);
  return <><section className={styles.section}><h2>Children</h2>{adding ? <ChildEditor onClose={() => setAdding(false)} /> : null}{children.map((child) => <ChildSettingsDisclosure child={child} key={child.id} />)}</section><SettingsSection title="Family"><SettingsRow control={<SettingsSwitch checked={childUpdates} label="Child activity updates" onChange={onChildUpdates} />} description="Receive changes from every child profile" title="Child activity updates" /><SettingsRow control={<button className={styles.add} onClick={() => setAdding(true)} type="button"><Plus />Add Child</button>} description="Create another child profile" title="Family profiles" /></SettingsSection></>;
}

function SettingsSection({ children: content, title }: { children: React.ReactNode; title: string }) { return <section className={styles.section}><h2>{title}</h2><div className={styles.group}>{content}</div></section>; }
