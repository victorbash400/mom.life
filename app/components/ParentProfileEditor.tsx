"use client";

import { useState, type FormEvent } from "react";
import { useFamily } from "./FamilyProvider";
import { ParentAvatar } from "./ParentAvatar";
import styles from "./ParentProfileEditor.module.css";

export function ParentProfileEditor() {
  const { family: { parent }, refresh } = useFamily();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const profile = await fetch("/api/family/parent", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: data.get("name"), email: data.get("email") }),
      });
      if (!profile.ok) {
        const result = await profile.json().catch(() => ({}));
        throw new Error(result.error || "Could not save profile.");
      }
      const photo = data.get("photo") as File;
      if (photo?.size) {
        const upload = new FormData();
        upload.set("file", photo);
        const response = await fetch("/api/family/parent/photo", { method: "PUT", body: upload });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || "Profile saved, but the photo could not be uploaded.");
        }
      }
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save profile.");
    } finally {
      setBusy(false);
    }
  }

  return <form className={styles.editor} onSubmit={submit}>
    <header><ParentAvatar parent={parent} size={76} /><label>{parent.has_photo ? "Change photo" : "Add photo"}<input accept="image/png,image/jpeg,image/webp" disabled={busy} name="photo" type="file" /></label></header>
    <label>Name<input defaultValue={parent.name} disabled={busy} maxLength={100} name="name" required /></label>
    <label>Email<input defaultValue={parent.email ?? ""} disabled={busy} maxLength={254} name="email" required type="email" /></label>
    {error ? <p role="alert">{error}</p> : null}
    <footer><button disabled={busy} type="submit">{busy ? "Saving…" : "Save"}</button></footer>
  </form>;
}
