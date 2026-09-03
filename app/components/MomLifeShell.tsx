"use client";
import { useState } from "react";
import { children } from "../data/dashboard";
import { useToolConnections } from "../hooks/useToolConnections";
import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import type { ParentSettingsView } from "./ParentSettingsWorkspace";
import { PluginQuickMenu } from "./PluginQuickMenu";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks" | "plugins" | "child" | "child-info" | "parent" | "parent-info" | "parent-settings" | "parent-tasks";
export function MomLifeShell() {
  const [mode, setMode] = useState<PanelMode>("home");
  const [pluginsOpen, setPluginsOpen] = useState(false);
  const [selectedChildId, setSelectedChildId] = useState<string>();
  const [parentSettingsView, setParentSettingsView] = useState<ParentSettingsView>("profile");
  const connections = useToolConnections();
  const selectedChild = children.find((child) => child.id === selectedChildId);
  function selectChild(id: string) { setSelectedChildId(id); setPluginsOpen(false); setMode((current) => current === "child-info" || current === "tasks" ? current : "child"); }
  function openParent() { setSelectedChildId(undefined); setPluginsOpen(false); setMode("parent"); }
  function openChildManagement() { setSelectedChildId(undefined); setPluginsOpen(false); setParentSettingsView("children"); setMode("parent-settings"); }
  function changeMode(next: PanelMode) { if (next === "parent-settings") setParentSettingsView("profile"); setMode(next); }
  function returnHome() { setSelectedChildId(undefined); setMode("home"); }
  return <main className={styles.shell} data-mode={mode}><AppHeader onChildrenOpen={openChildManagement} onProfileOpen={openParent} pluginsOpen={pluginsOpen} onPluginsToggle={() => setPluginsOpen((open) => !open)} />{pluginsOpen ? <PluginQuickMenu connectedIds={connections.connectedIds} onClose={() => setPluginsOpen(false)} onDisconnect={connections.disconnect} onStore={() => { setPluginsOpen(false); setMode("plugins"); }} /> : null}<ChildSwitcher focused={mode === "child" || mode === "child-info" || (mode === "tasks" && Boolean(selectedChild))} onSelect={selectChild} selectedId={selectedChildId} /><ActionPanel child={selectedChild} connections={connections} mode={mode} onModeChange={changeMode} onReturnHome={returnHome} parentSettingsView={parentSettingsView} /></main>;
}
