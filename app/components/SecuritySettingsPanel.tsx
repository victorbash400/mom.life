"use client";

import { useState } from "react";

import type { SecurityAlertLevel, SecuritySettings } from "../types/security";
import { useFamily } from "./FamilyProvider";
import { SecurityScopeControls } from "./SecurityScopeControls";
import { SecurityCheckButton } from "./SecurityCheckButton";
import { SettingsRow } from "./SettingsRow";
import { SettingsSwitch } from "./SettingsSwitch";
import styles from "./SecuritySettingsPanel.module.css";

export function SecuritySettingsPanel({ settings, onSave }: { settings: SecuritySettings; onSave: (settings: Omit<SecuritySettings, "family_id" | "updated_at">) => Promise<void> }) {
  const [enabled, setEnabled] = useState(settings.enabled);
  const [alertLevel, setAlertLevel] = useState<SecurityAlertLevel>(settings.alert_level);
  const [instructions, setInstructions] = useState(settings.instructions);
  const { family } = useFamily();
  const [policy, setPolicy] = useState({ sources: settings.sources, child_ids: settings.child_ids, depth: settings.depth, review_mode: settings.review_mode, channel: settings.channel });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string>();
  async function save() {
    setBusy(true); setSaved(false); setError(undefined);
    try { await onSave({ enabled, alert_level: alertLevel, instructions, ...policy }); setSaved(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save safety settings."); }
    finally { setBusy(false); }
  }
  return <section className={styles.settings}><div className={styles.group}><SettingsRow control={<SettingsSwitch checked={enabled} label="Safety monitoring" onChange={setEnabled} />} title="Monitoring" /><SettingsRow control={<select aria-label="Safety alert level" disabled={!enabled || busy} onChange={(event) => setAlertLevel(event.target.value as SecurityAlertLevel)} value={alertLevel}><option value="urgent">Urgent only</option><option value="important">Important</option><option value="all">All credible concerns</option></select>} title="Alert level" /><SecurityScopeControls policy={policy} onChange={setPolicy} childrenProfiles={family.children} disabled={busy || !enabled} /><label className={styles.instructions}><span>Instructions</span><textarea disabled={!enabled || busy} maxLength={4000} onChange={(event) => setInstructions(event.target.value)} placeholder="What should the Safety Agent alert you about?" rows={5} value={instructions} /></label></div><SecurityCheckButton disabled={busy || !enabled} /><footer>{error ? <small role="alert">{error}</small> : saved ? <small>Saved</small> : <span />}<button disabled={busy} onClick={() => void save()} type="button">{busy ? "Saving…" : "Save"}</button></footer></section>;
}
