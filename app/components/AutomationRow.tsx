import { Clock3, HeartPulse, Inbox, Pause, Pencil, Play, Trash2, Zap } from "lucide-react";
import { useState } from "react";
import type { Automation } from "../types/automations";
import { AutomationChecks } from "./AutomationChecks";
import { AutomationInstructionEditor } from "./AutomationInstructionEditor";
import styles from "./AutomationList.module.css";
export function AutomationRow({ item, childName, change }: { item: Automation; childName: string; change: (id: string, method: string, body?: object) => Promise<void> }) {
  const [checksOpen, setChecksOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const Icon = item.trigger === "time" ? Clock3 : item.trigger === "health" ? HeartPulse : Inbox;
  async function act(method: string, body?: object, suffix = "") { setBusy(true); setError(""); try { await change(item.id + suffix, method, body); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update automation."); } finally { setBusy(false); } }
  const status = item.scheduler_state === "failed" ? "Check failed" : item.scheduler_state === "completed" ? "Finished" : item.scheduler_state === "error" ? "Setup required" : !item.enabled ? "Paused" : item.task_status === "paused" ? "Task paused" : "Enabled";
  return <li className={styles.row}><Icon aria-hidden="true" size={14} /><div><strong>{item.instruction}</strong><small>{childName} · {status} · {item.trigger === "time" ? `${item.schedule} · ${item.timezone}` : item.trigger === "health" ? "On health updates" : "On incoming information"}</small><details onToggle={(event) => setChecksOpen(event.currentTarget.open)}><summary>{item.task_text}</summary><p>{item.last_checked_at ? `Last checked ${new Date(item.last_checked_at).toLocaleString()}` : "Not checked yet"}</p>{item.last_result && <p>{item.last_result}</p>}{checksOpen && <AutomationChecks automationId={item.id} />}</details>{editing && <AutomationInstructionEditor instruction={item.instruction} onCancel={() => setEditing(false)} onSave={(instruction) => change(item.id, "PATCH", { instruction, enabled: item.enabled })} />}{(error || item.failure) && <p role="alert">{error || item.failure}</p>}</div><span className={styles.actions}><button aria-label="Check automation now" disabled={busy || !item.enabled || item.task_status === "paused"} onClick={() => void act("POST", undefined, "/run")} type="button"><Zap size={14} /></button><button aria-label={item.enabled ? "Pause automation" : "Resume automation"} disabled={busy} onClick={() => void act("PATCH", { enabled: !item.enabled })} type="button">{item.enabled ? <Pause size={14} /> : <Play size={14} />}</button><button aria-label="Edit automation instruction" disabled={busy} onClick={() => setEditing(!editing)} type="button"><Pencil size={14} /></button><button aria-label="Delete automation" disabled={busy} onClick={() => void act("DELETE")} type="button"><Trash2 size={14} /></button></span></li>;
}
