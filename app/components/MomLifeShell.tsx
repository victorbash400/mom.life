"use client";

import { useState } from "react";
import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import { PluginQuickMenu } from "./PluginQuickMenu";
import { useToolConnections } from "../hooks/useToolConnections";
import { children } from "../data/dashboard";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks" | "plugins" | "child" | "child-info";

export function MomLifeShell() {
  const [mode, setMode] = useState<PanelMode>("home");
  const [pluginsOpen, setPluginsOpen] = useState(false);
  const [selectedChildId, setSelectedChildId] = useState<string>();
  const connections = useToolConnections();
  const selectedChild = children.find((child) => child.id === selectedChildId);
  function selectChild(id: string) { setSelectedChildId(id); setPluginsOpen(false); setMode("child"); }
  function returnHome() { setSelectedChildId(undefined); setMode("home"); }
  return <main className={styles.shell} data-mode={mode}><AppHeader pluginsOpen={pluginsOpen} onPluginsToggle={() => setPluginsOpen((open) => !open)} />{pluginsOpen ? <PluginQuickMenu connectedIds={connections.connectedIds} onClose={() => setPluginsOpen(false)} onDisconnect={connections.disconnect} onStore={() => { setPluginsOpen(false); setMode("plugins"); }} /> : null}<ChildSwitcher focused={mode === "child" || mode === "child-info" || (mode === "tasks" && Boolean(selectedChild))} onSelect={selectChild} selectedId={selectedChildId} /><ActionPanel child={selectedChild} connections={connections} mode={mode} onModeChange={setMode} onReturnHome={returnHome} /></main>;
}
