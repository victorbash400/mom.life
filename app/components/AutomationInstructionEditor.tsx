import { useState } from "react";
import styles from "./AutomationList.module.css";
export function AutomationInstructionEditor({ instruction, onSave, onCancel }: { instruction: string; onSave: (instruction: string) => Promise<void>; onCancel: () => void }) {
  const [value, setValue] = useState(instruction);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() { setBusy(true); try { await onSave(value); onCancel(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save automation."); } finally { setBusy(false); } }
  return <div className={styles.editor}><textarea aria-label="Automation instruction" disabled={busy} maxLength={4000} onChange={(event) => setValue(event.target.value)} value={value} />{error && <p role="alert">{error}</p>}<div><button disabled={busy} onClick={onCancel} type="button">Cancel</button><button disabled={busy || !value.trim()} onClick={() => void save()} type="button">Save</button></div></div>;
}
