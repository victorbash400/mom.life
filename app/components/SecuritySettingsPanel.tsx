"use client";

import { useState } from "react";

import type { SecurityAlertLevel, SecuritySettings } from "../types/security";
import { SettingsRow } from "./SettingsRow";
import { SettingsSwitch } from "./SettingsSwitch";
import styles from "./SecuritySettingsPanel.module.css";

export function SecuritySettingsPanel({ settings, onSave }: { settings: SecuritySettings; onSave: (settings: Pick<SecuritySettings, "enabled" | "alert_level" | "instructions">) => Promise<void> }) {
  const [enabled, setEnabled] = useState(settings.enabled);
  const [alertLevel, setAlertLevel] = useState<SecurityAlertLevel>(settings.alert_level);
  const [instructions, setInstructions] = useState(settings.instructions);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string>();
  async function save() {
    setBusy(true); setSaved(false); setError(undefined);
    try { await onSave({ enabled, alert_level: alertLevel, instructions }); setSaved(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save security settings."); }
    finally { setBusy(false); }
  }
  return <section className={styles.settings}><div className={styles.group}><SettingsRow control={<SettingsSwitch checked={enabled} label="Security monitoring" onChange={setEnabled} />} title="Monitoring" /><SettingsRow control={<select aria-label="Security alert level" disabled={!enabled || busy} onChange={(event) => setAlertLevel(event.target.value as SecurityAlertLevel)} value={alertLevel}><option value="urgent">Urgent only</option><option value="important">Important</option><option value="all">All credible concerns</option></select>} title="Alert level" /><label className={styles.instructions}><span>Instructions</span><textarea disabled={!enabled || busy} maxLength={4000} onChange={(event) => setInstructions(event.target.value)} placeholder="What should the Security Agent alert you about?" rows={5} value={instructions} /></label></div><footer>{error ? <small role="alert">{error}</small> : saved ? <small>Saved</small> : <span />}<button disabled={busy} onClick={() => void save()} type="button">{busy ? "Saving…" : "Save"}</button></footer></section>;
}
