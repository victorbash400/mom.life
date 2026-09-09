import { ClipboardCheck, SquarePen } from "lucide-react";

import { useFamily } from "./FamilyProvider";
import type { useToolConnections } from "../hooks/useToolConnections";
import type { useSecurity } from "../hooks/useSecurity";
import type { ChildProfile } from "../types/dashboard";
import { AskWorkspace } from "./AskWorkspace";
import { ChildInformationWorkspace } from "./ChildInformationWorkspace";
import { ChildProfileWorkspace } from "./ChildProfileWorkspace";
import { EducationWorkspace } from "./EducationWorkspace";
import { IntakeWorkspace } from "./IntakeWorkspace";
import type { PanelMode } from "./MomLifeShell";
import { OrganicPanelSurface } from "./OrganicPanelSurface";
import { ParentProfileWorkspace } from "./ParentProfileWorkspace";
import { ParentSettingsWorkspace, type ParentSettingsView } from "./ParentSettingsWorkspace";
import { PluginStore } from "./PluginStore";
import { TasksWorkspace } from "./TasksWorkspace";
import { SecurityWorkspace } from "./SecurityWorkspace";
import { UtilityNav } from "./UtilityNav";
import styles from "./ActionPanel.module.css";

type Connections = ReturnType<typeof useToolConnections>;
type SecurityState = ReturnType<typeof useSecurity>;
type Props = { child?: ChildProfile; connections: Connections; mode: PanelMode; parentSettingsView: ParentSettingsView; security: SecurityState; onModeChange: (mode: PanelMode) => void; onReturnHome: () => void };

export function ActionPanel({ child, connections, mode, parentSettingsView, security, onModeChange, onReturnHome }: Props) {
  const { family: { parent } } = useFamily();
  const closeTasks = child ? () => onModeChange("child") : () => onModeChange("home");
  return <section className={styles.panel} data-mode={mode}><OrganicPanelSurface mode={mode} />{mode === "home" ? <HomeActions connections={connections} onModeChange={onModeChange} /> : null}{mode === "ask" ? <AskWorkspace onClose={() => onModeChange("home")} /> : null}{mode === "incoming" ? <IntakeWorkspace onClose={() => onModeChange("home")} /> : null}{mode === "education" ? <EducationWorkspace child={child} onClose={() => onModeChange("home")} /> : null}{mode === "security" ? <SecurityWorkspace onClose={() => onModeChange("home")} security={security} /> : null}{mode === "tasks" ? <TasksWorkspace initialChild={child?.id} onClose={closeTasks} /> : null}{mode === "parent-tasks" ? <TasksWorkspace onClose={() => onModeChange("parent")} /> : null}{mode === "plugins" ? <PluginStore connections={connections} onBack={() => onModeChange("home")} /> : null}{mode === "child" && child ? <ChildProfileWorkspace child={child} onBack={onReturnHome} onInformation={() => onModeChange("child-info")} onTasks={() => onModeChange("tasks")} /> : null}{mode === "child-info" && child ? <ChildInformationWorkspace child profile={child} onBack={() => onModeChange("child")} /> : null}{mode === "parent" ? <ParentProfileWorkspace onBack={onReturnHome} onInformation={() => onModeChange("parent-info")} onSettings={() => onModeChange("parent-settings")} onTasks={() => onModeChange("parent-tasks")} /> : null}{mode === "parent-info" ? <ChildInformationWorkspace profile={parent} onBack={() => onModeChange("parent")} /> : null}{mode === "parent-settings" ? <ParentSettingsWorkspace initialView={parentSettingsView} key={parentSettingsView} onBack={() => onModeChange("parent")} /> : null}</section>;
}

function HomeActions({ connections, onModeChange }: Pick<Props, "connections" | "onModeChange">) {
  return <><h1><span>mom.</span><em>life</em></h1><div className={styles.primaryActions}><button className={styles.ask} onClick={() => onModeChange("ask")} type="button"><SquarePen /><span>Ask</span></button><button className={styles.tasks} onClick={() => onModeChange("tasks")} type="button"><ClipboardCheck /><span>Tasks</span></button></div>{connections.loaded ? <UtilityNav connectedIds={connections.connectedIds} /> : null}</>;
}
