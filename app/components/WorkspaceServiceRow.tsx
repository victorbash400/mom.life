import { CalendarDays, FileText, HardDrive, Mail } from "lucide-react";

import type { ToolPermission } from "../data/toolDirectory";
import styles from "./WorkspaceServiceRow.module.css";

export const workspaceServices = [
  { id: "google-workspace.0", name: "Gmail", icon: Mail, detail: "Read mail and prepare drafts" },
  { id: "google-workspace.1", name: "Google Drive", icon: HardDrive, detail: "Find and organize family files" },
  { id: "google-workspace.2", name: "Google Docs", icon: FileText, detail: "Read and update family documents" },
  { id: "google-workspace.3", name: "Google Calendar", icon: CalendarDays, detail: "Read and manage requested family events" },
];

export function WorkspaceServiceRow({ connected, disabled, index, onToggle, permission }: { connected: boolean; disabled: boolean; index: number; onToggle: () => void; permission: ToolPermission }) {
  const service = workspaceServices[index] || workspaceServices[2];
  const Icon = service.icon;
  const enabled = connected && permission.enabled;
  return <article className={styles.row}><span className={styles.icon}><Icon aria-hidden="true" /></span><span className={styles.copy}><strong>{service.name}</strong><small>{service.detail}</small></span><button aria-checked={enabled} aria-label={`${enabled ? "Disable" : "Enable"} ${service.name}`} className={styles.switch} disabled={disabled || !connected} onClick={onToggle} role="switch" type="button"><span /></button></article>;
}
