"use client";
import { useState, type FormEvent } from "react";
import type { ChildProfile } from "../types/dashboard";
import { SettingsSwitch } from "./SettingsSwitch";
import { useFamily } from "./FamilyProvider";
import styles from "./ChildEditor.module.css";
export function ChildEditor({ child, onClose }: { child?: ChildProfile; onClose: () => void }) {
  const { refresh } = useFamily();
  const [notifications, setNotifications] = useState(child?.notifications ?? true);
  const [photoName, setPhotoName] = useState("");
  const [savedId, setSavedId] = useState(child?.id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); setError("");
    try {
      const response = await fetch(`/api/family/children${savedId ? `/${savedId}` : ""}`, { method: savedId ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name"), birth_date: data.get("birth_date") || null, email_updates: child?.email_updates ?? true, text_updates: child?.text_updates ?? false, notifications }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not save child.");
      setSavedId(result.id);
      const photo = data.get("photo") as File;
      if (photo?.size) {
        const upload = new FormData(); upload.set("file", photo);
        const saved = await fetch(`/api/family/children/${result.id}/photo`, { method: "PUT", body: upload });
        if (!saved.ok) { await refresh(); throw new Error("Profile saved, but the photo could not be uploaded. Edit the profile to try again."); }
      }
      await refresh(); onClose();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save child."); } finally { setBusy(false); }
  }
  return <form className={styles.editor} onSubmit={submit}><label>Name<input name="name" required maxLength={100} defaultValue={child?.name} disabled={busy} /></label><label>Date of birth<input type="date" name="birth_date" defaultValue={child?.birth_date ?? ""} max={new Date().toISOString().slice(0,10)} disabled={busy} /></label><div className={styles.photo}><span>Photo</span><label className={styles.upload}>{photoName || "Upload"}<input type="file" name="photo" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={(event) => setPhotoName(event.target.files?.[0]?.name ?? "")} /></label></div><div className={styles.check}><span>Notifications</span><SettingsSwitch checked={notifications} label="Child notifications" onChange={(value) => { if (!busy) setNotifications(value); }} /></div>{error ? <p role="alert">{error}</p> : null}<footer><button type="button" onClick={onClose} disabled={busy}>Cancel</button><button type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button></footer></form>;
}
