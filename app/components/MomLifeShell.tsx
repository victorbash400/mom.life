"use client";

import { useState } from "react";

import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import { useFamily } from "./FamilyProvider";
import type { ParentSettingsView } from "./ParentSettingsWorkspace";
import { useToolConnections } from "../hooks/useToolConnections";
import { useSecurity } from "../hooks/useSecurity";
import { useSimulator } from "../hooks/useSimulator";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks" | "calendar" | "incoming" | "education" | "security" | "plugins" | "simulator" | "child" | "child-info" | "parent" | "parent-info" | "parent-settings" | "parent-tasks";

export function MomLifeShell() {
  const { family: { children } } = useFamily();
  const [mode, setMode] = useState<PanelMode>("home");
  const [selectedChildId, setSelectedChildId] = useState<string>();
  const [parentSettingsView, setParentSettingsView] = useState<ParentSettingsView>("profile");
  const connections = useToolConnections();
  const security = useSecurity();
  const simulator = useSimulator(connections.refresh);
  const visibleMode = (mode === "child" || mode === "child-info") && !children.some((child) => child.id === selectedChildId) ? "home" : mode;
  const selectedChild = children.find((child) => child.id === selectedChildId);

  function selectChild(id: string) { setSelectedChildId(id); setMode((current) => current === "child-info" || current === "tasks" || current === "education" ? current : "child"); }
  function openParent() { setSelectedChildId(undefined); setMode("parent"); }
  function openChildManagement() { setSelectedChildId(undefined); setParentSettingsView("children"); setMode("parent-settings"); }
  function openCalendar() { setSelectedChildId(undefined); setMode("calendar"); }
  function openIncoming() { setSelectedChildId(undefined); setMode("incoming"); }
  function openEducation() { setSelectedChildId((current) => current ?? children[0]?.id); setMode("education"); }
  function openSecurity() { setSelectedChildId(undefined); setMode("security"); }
  function openPlugins() { setSelectedChildId(undefined); setMode("plugins"); }
  function openSimulator() { setSelectedChildId(undefined); void simulator.refresh(); setMode("simulator"); }
  function changeMode(next: PanelMode) { if (next === "parent-settings") setParentSettingsView("profile"); setMode(next); }
  function returnHome() { setSelectedChildId(undefined); setMode("home"); }

  return <main className={styles.shell} data-mode={visibleMode}><AppHeader calendarOpen={visibleMode === "calendar"} educationOpen={visibleMode === "education"} incomingOpen={visibleMode === "incoming"} onCalendarOpen={openCalendar} onChildrenOpen={openChildManagement} onEducationOpen={openEducation} onIncomingOpen={openIncoming} onProfileOpen={openParent} pluginsOpen={visibleMode === "plugins"} onPluginsOpen={openPlugins} onSecurityOpen={openSecurity} onSimulatorOpen={openSimulator} securityAlertCount={security.reviews.filter((review) => !review.dismissed).length} securityOpen={visibleMode === "security"} simulatorOpen={visibleMode === "simulator"} /><ChildSwitcher focused={mode === "child" || mode === "child-info" || mode === "education" || (mode === "tasks" && Boolean(selectedChild))} onSelect={selectChild} selectedId={selectedChildId} /><ActionPanel child={selectedChild} connections={connections} mode={visibleMode} onModeChange={changeMode} onReturnHome={returnHome} parentSettingsView={parentSettingsView} security={security} simulator={simulator} /></main>;
}
