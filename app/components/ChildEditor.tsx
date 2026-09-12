"use client";

import { UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { ChildProfile } from "../types/dashboard";
import { childAvatarStyle } from "./ChildAvatar";
import { useFamily } from "./FamilyProvider";
import styles from "./ChildEditor.module.css";

export function ChildEditor({ child, onClose }: { child?: ChildProfile; onClose: () => void }) {
  const { refresh } = useFamily();
  const [savedId, setSavedId] = useState(child?.id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/family/children${savedId ? `/${savedId}` : ""}`, {
        method: savedId ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: data.get("name"), birth_date: data.get("birth_date") || null, email_updates: child?.email_updates ?? true, text_updates: child?.text_updates ?? false, notifications: child?.notifications ?? true }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not save child.");
      setSavedId(result.id);
      const photo = data.get("photo") as File;
      if (photo?.size) {
        const upload = new FormData();
        upload.set("file", photo);
        const saved = await fetch(`/api/family/children/${result.id}/photo`, { method: "PUT", body: upload });
        if (!saved.ok) throw new Error("Profile saved, but the photo could not be uploaded.");
      }
      await refresh();
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save child.");
    } finally {
      setBusy(false);
    }
  }

  return <form className={styles.editor} onSubmit={submit}>
    <header>{child ? <i aria-label={child.name} style={childAvatarStyle(child)} /> : <UserRound aria-hidden="true" />}<label>{child?.has_photo ? "Change photo" : "Add photo"}<input accept="image/png,image/jpeg,image/webp" disabled={busy} name="photo" type="file" /></label></header>
    <label>Name<input defaultValue={child?.name} disabled={busy} maxLength={100} name="name" required /></label>
    <label>Date of birth<input defaultValue={child?.birth_date ?? ""} disabled={busy} max={new Date().toISOString().slice(0,10)} name="birth_date" type="date" /></label>
    {error ? <p role="alert">{error}</p> : null}
    <footer><button disabled={busy} onClick={onClose} type="button">Cancel</button><button disabled={busy} type="submit">{busy ? "Saving…" : "Save"}</button></footer>
  </form>;
}
