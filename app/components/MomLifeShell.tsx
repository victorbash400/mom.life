"use client";

import { useState } from "react";
import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import { PluginQuickMenu } from "./PluginQuickMenu";
import { useToolConnections } from "../hooks/useToolConnections";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks" | "plugins";

export function MomLifeShell() {
  const [mode, setMode] = useState<PanelMode>("home");
  const [pluginsOpen, setPluginsOpen] = useState(false);
  const connections = useToolConnections();
  return <main className={styles.shell} data-mode={mode}><AppHeader pluginsOpen={pluginsOpen} onPluginsToggle={() => setPluginsOpen((open) => !open)} />{pluginsOpen ? <PluginQuickMenu connectedIds={connections.connectedIds} onClose={() => setPluginsOpen(false)} onDisconnect={connections.disconnect} onStore={() => { setPluginsOpen(false); setMode("plugins"); }} /> : null}<ChildSwitcher /><ActionPanel connections={connections} mode={mode} onModeChange={setMode} /></main>;
}
