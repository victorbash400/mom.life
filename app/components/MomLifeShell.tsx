"use client";

import { useState } from "react";

import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import { useFamily } from "./FamilyProvider";
import type { ParentSettingsView } from "./ParentSettingsWorkspace";
import { useToolConnections } from "../hooks/useToolConnections";
import { useSecurity } from "../hooks/useSecurity";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks" | "incoming" | "security" | "plugins" | "child" | "child-info" | "parent" | "parent-info" | "parent-settings" | "parent-tasks";

export function MomLifeShell() {
  const { family: { children } } = useFamily();
  const [mode, setMode] = useState<PanelMode>("home");
  const [selectedChildId, setSelectedChildId] = useState<string>();
  const [parentSettingsView, setParentSettingsView] = useState<ParentSettingsView>("profile");
  const connections = useToolConnections();
  const security = useSecurity();
  const visibleMode = (mode === "child" || mode === "child-info") && !children.some((child) => child.id === selectedChildId) ? "home" : mode;
  const selectedChild = children.find((child) => child.id === selectedChildId);

  function selectChild(id: string) { setSelectedChildId(id); setMode((current) => current === "child-info" || current === "tasks" ? current : "child"); }
  function openParent() { setSelectedChildId(undefined); setMode("parent"); }
  function openChildManagement() { setSelectedChildId(undefined); setParentSettingsView("children"); setMode("parent-settings"); }
  function openIncoming() { setSelectedChildId(undefined); setMode("incoming"); }
  function openSecurity() { setSelectedChildId(undefined); setMode("security"); }
  function openPlugins() { setSelectedChildId(undefined); setMode("plugins"); }
  function changeMode(next: PanelMode) { if (next === "parent-settings") setParentSettingsView("profile"); setMode(next); }
  function returnHome() { setSelectedChildId(undefined); setMode("home"); }

  return <main className={styles.shell} data-mode={visibleMode}><AppHeader incomingOpen={visibleMode === "incoming"} onChildrenOpen={openChildManagement} onIncomingOpen={openIncoming} onProfileOpen={openParent} pluginsOpen={visibleMode === "plugins"} onPluginsOpen={openPlugins} onSecurityOpen={openSecurity} securityAlertCount={security.reviews.filter((review) => !review.dismissed).length} securityOpen={visibleMode === "security"} /><ChildSwitcher focused={mode === "child" || mode === "child-info" || (mode === "tasks" && Boolean(selectedChild))} onSelect={selectChild} selectedId={selectedChildId} /><ActionPanel child={selectedChild} connections={connections} mode={visibleMode} onModeChange={changeMode} onReturnHome={returnHome} parentSettingsView={parentSettingsView} security={security} /></main>;
}
