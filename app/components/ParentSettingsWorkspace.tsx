"use client";
import { ChildEditor } from "./ChildEditor";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useFamily } from "./FamilyProvider";
import { useProfileSources } from "../hooks/useProfileSources";
import { ParentProfileEditor } from "./ParentProfileEditor";
import { ProfileSources } from "./ProfileSources";
import { SettingsRow } from "./SettingsRow";
import { ChildSettingsDisclosure } from "./ChildSettingsDisclosure";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./ParentSettingsWorkspace.module.css";

export type ParentSettingsView = "profile" | "children";
export function ParentSettingsWorkspace({ initialView = "profile", onBack }: { initialView?: ParentSettingsView; onBack: () => void }) {
  const { family: { parent } } = useFamily();
  const [view, setView] = useState<ParentSettingsView>(initialView);
  const profileSources = useProfileSources();
  return <section className={styles.workspace}><header className={styles.header}><WorkspaceHeader backLabel={`Back to ${parent.name}`} title="Settings" onClose={onBack} /><nav aria-label="Settings section"><button aria-pressed={view === "profile"} onClick={() => setView("profile")} type="button">Profile</button><button aria-pressed={view === "children"} onClick={() => setView("children")} type="button">Child Management</button></nav></header><div className={styles.scroll}>{view === "profile" ? <section className={styles.profile}><ParentProfileEditor /><ProfileSources {...profileSources} profileId="parent" profileName={parent.name} onToggle={(profileId,pluginId,enabled) => void profileSources.toggle(profileId,pluginId,enabled)} /></section> : <ChildSettings profileSources={profileSources} />}</div></section>;
}

function ChildSettings({ profileSources }: { profileSources: ReturnType<typeof useProfileSources> }) {
  const { family: { children } } = useFamily();
  const [adding, setAdding] = useState(false);
  return <><section className={styles.section}><h2>Children</h2>{adding ? <ChildEditor onClose={() => setAdding(false)} /> : null}{children.map((child) => <ChildSettingsDisclosure child={child} key={child.id} profileSources={profileSources} />)}</section><SettingsSection title="Family"><SettingsRow control={<button className={styles.add} onClick={() => setAdding(true)} type="button"><Plus />Add Child</button>} title="Family profiles" /></SettingsSection></>;
}

function SettingsSection({ children: content, title }: { children: React.ReactNode; title: string }) { return <section className={styles.section}><h2>{title}</h2><div className={styles.group}>{content}</div></section>; }
