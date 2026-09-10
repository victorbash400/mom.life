"use client";

import { Activity, MessageCircle, PlugZap } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./SimulatorDevice.module.css";


const apps = [
  { id: "whatsapp", name: "WhatsApp", icon: MessageCircle },
  { id: "health", name: "Health", icon: Activity },
  { id: "connections", name: "Connections", icon: PlugZap },
] as const;

export type SimulatorView = typeof apps[number]["id"];

export function SimulatorDevice({ children, onViewChange, view }: { children: ReactNode; onViewChange: (view: SimulatorView) => void; view: SimulatorView }) {
  const selected = apps.find((app) => app.id === view)!;
  const SelectedIcon = selected.icon;
  return <section aria-label="Family simulator" className={styles.device}>
    <aside><nav aria-label="Simulator apps">{apps.map((app) => { const Icon = app.icon; return <button aria-pressed={view === app.id} data-app={app.id} key={app.id} onClick={() => onViewChange(app.id)} type="button"><i><Icon aria-hidden="true" /></i><span>{app.name}</span></button>; })}</nav></aside>
    <main><header><SelectedIcon aria-hidden="true" /><strong>{selected.name}</strong><small>Simulator</small></header><div className={styles.content}>{children}</div></main>
  </section>;
}
