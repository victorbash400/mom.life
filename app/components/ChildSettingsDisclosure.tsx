"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { useProfileSources } from "../hooks/useProfileSources";
import type { ChildProfile } from "../types/dashboard";
import { childAvatarStyle } from "./ChildAvatar";
import { ChildEditor } from "./ChildEditor";
import { useFamily } from "./FamilyProvider";
import { ProfileSources } from "./ProfileSources";
import { SettingsRow } from "./SettingsRow";
import { SettingsSwitch } from "./SettingsSwitch";
import styles from "./ChildSettingsDisclosure.module.css";

type Sources = ReturnType<typeof useProfileSources>;

export function ChildSettingsDisclosure({ child, profileSources }: { child: ChildProfile; profileSources: Sources }) {
  const { refresh } = useFamily();
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save(changes: Partial<ChildProfile>, remove = false) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/family/children/${child.id}`, {
        method: remove ? "DELETE" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: remove ? undefined : JSON.stringify({ name: child.name, birth_date: child.birth_date, email_updates: child.email_updates, text_updates: child.text_updates, notifications: child.notifications, ...changes }),
      });
      if (!response.ok) throw new Error("Could not update child.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update child.");
    } finally {
      setBusy(false);
    }
  }

  return <details className={styles.child}>
    <summary><i style={childAvatarStyle(child)} /><span><strong>{child.name}</strong><small>{child.age}</small></span><ChevronDown /></summary>
    <section>
      {editing ? <ChildEditor child={child} onClose={() => setEditing(false)} /> : <SettingsRow title="Profile" control={<button className={styles.photo} onClick={() => setEditing(true)} type="button">Edit</button>} />}
      <SettingsRow title="Updates through" control={<div className={styles.methods} role="group" aria-label={`${child.name} updates`}><button type="button" disabled={busy} aria-pressed={child.email_updates} onClick={() => void save({ email_updates: !child.email_updates })}>Email</button><button type="button" disabled={busy} aria-pressed={child.text_updates} onClick={() => void save({ text_updates: !child.text_updates })}>Text</button></div>} />
      <SettingsRow title="Notifications" control={<SettingsSwitch checked={child.notifications} disabled={busy} label={`${child.name} notifications`} onChange={(notifications) => void save({ notifications })} />} />
      <ProfileSources {...profileSources} embedded profileId={child.id} profileName={child.name} onToggle={(profileId,pluginId,enabled) => void profileSources.toggle(profileId,pluginId,enabled)} />
      <SettingsRow title={removing ? "Remove this child and their files?" : "Child profile"} control={<div className={styles.methods}>{removing ? <button type="button" onClick={() => setRemoving(false)}>Cancel</button> : null}<button disabled={busy} type="button" onClick={() => removing ? void save({},true) : setRemoving(true)}>Remove</button></div>} />
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </section>
  </details>;
}
