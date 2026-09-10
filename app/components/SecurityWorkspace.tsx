"use client";

import { useState } from "react";

import type { useSecurity } from "../hooks/useSecurity";
import { SecurityDashboard } from "./SecurityDashboard";
import { SecuritySettingsPanel } from "./SecuritySettingsPanel";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./SecurityWorkspace.module.css";

type SecurityState = ReturnType<typeof useSecurity>;

export function SecurityWorkspace({ security, onClose }: { security: SecurityState; onClose: () => void }) {
  const [view, setView] = useState<"alerts" | "settings">("alerts");
  const [selectedId, setSelectedId] = useState<string>();
  const reviews = security.reviews;
  const active = reviews.filter((review) => !review.dismissed);
  return <section className={styles.workspace}><header><WorkspaceHeader title="Safety" onClose={onClose} /><nav aria-label="Safety section"><button aria-pressed={view === "alerts"} onClick={() => setView("alerts")} type="button">Alerts</button><button aria-pressed={view === "settings"} onClick={() => setView("settings")} type="button">Settings</button></nav></header>{security.error ? <p className={styles.error} role="alert">{security.error}</p> : null}{security.loaded ? view === "alerts" ? <section className={styles.panel}><header><strong>Safety alerts</strong><small>{active.length} active</small></header><SecurityDashboard onDismiss={security.dismiss} onRetry={security.retry} onSelect={setSelectedId} reviews={reviews} selectedId={selectedId} /></section> : security.settings ? <SecuritySettingsPanel onSave={security.saveSettings} settings={security.settings} /> : null : null}</section>;
}
