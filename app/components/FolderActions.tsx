"use client";
import { useState, type FormEvent } from "react";
import type { ChildDataNode } from "../types/childData";
import styles from "./FolderActions.module.css";
export function FolderActions({ childId, parentId, selected, onSaved }: { childId: string; parentId?: string; selected?: ChildDataNode; onSaved: () => Promise<void> }) {
  const [creating, setCreating] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function mutate(path: string, init: RequestInit) {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/family/children/${childId}/${path}`, init);
      if (!response.ok) { const body = await response.json(); throw new Error(body.error || "Could not save changes."); }
      await onSaved(); setCreating(false); setRemoving(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save changes."); } finally { setBusy(false); }
  }
  function folder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const name = new FormData(event.currentTarget).get("name");
    void mutate("folders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, parent_id: parentId ?? null }) });
  }
  return <div className={styles.actions}><button disabled={busy} onClick={() => setCreating(!creating)} type="button">New folder</button><label>Upload<input type="file" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; const data = new FormData(); data.set("file", file); if (parentId) data.set("parent_id", parentId); void mutate("files", { method: "POST", body: data }); event.target.value = ""; }} /></label>{selected ? <><button type="button" disabled={busy} onClick={() => setRemoving(!removing)}>Remove</button>{selected.kind === "file" ? <a href={`/api/family/children/${childId}/files/${selected.id}`} download>Download</a> : null}</> : null}{creating ? <form onSubmit={folder}><input aria-label="Folder name" name="name" required maxLength={180} autoFocus /><button disabled={busy} type="submit">Create</button></form> : null}{removing && selected ? <span>Remove {selected.name}{selected.kind === "folder" ? " and its contents" : ""}? <button disabled={busy} type="button" onClick={() => void mutate(`nodes/${selected.id}`, { method: "DELETE" })}>Remove</button><button type="button" onClick={() => setRemoving(false)}>Cancel</button></span> : null}{error ? <p role="alert">{error}</p> : null}</div>;
}
