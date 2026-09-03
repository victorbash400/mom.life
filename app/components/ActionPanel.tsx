import { ClipboardCheck, SquarePen } from "lucide-react";
import type { PanelMode } from "./MomLifeShell";
import { AskWorkspace } from "./AskWorkspace";
import { OrganicPanelSurface } from "./OrganicPanelSurface";
import { TasksWorkspace } from "./TasksWorkspace";
import { PluginStore } from "./PluginStore";
import type { useToolConnections } from "../hooks/useToolConnections";
import type { ChildProfile } from "../types/dashboard";
import { ChildProfileWorkspace } from "./ChildProfileWorkspace";
import { ChildInformationWorkspace } from "./ChildInformationWorkspace";
import { UtilityNav } from "./UtilityNav";
import styles from "./ActionPanel.module.css";

type Connections = ReturnType<typeof useToolConnections>;
type ActionPanelProps = { child?: ChildProfile; connections: Connections; mode: PanelMode; onModeChange: (mode: PanelMode) => void; onReturnHome: () => void };

export function ActionPanel({ child, connections, mode, onModeChange, onReturnHome }: ActionPanelProps) {
  const closeTasks = child ? () => onModeChange("child") : () => onModeChange("home");
  return <section className={styles.panel} data-mode={mode}><OrganicPanelSurface mode={mode} />{mode === "home" ? <HomeActions connections={connections} onModeChange={onModeChange} /> : null}{mode === "ask" ? <AskWorkspace onClose={() => onModeChange("home")} /> : null}{mode === "tasks" ? <TasksWorkspace initialChild={child?.id} onClose={closeTasks} /> : null}{mode === "plugins" ? <PluginStore connectedIds={connections.connectedIds} onBack={() => onModeChange("home")} onConnect={connections.connect} onDisconnect={connections.disconnect} /> : null}{mode === "child" && child ? <ChildProfileWorkspace child={child} onBack={onReturnHome} onInformation={() => onModeChange("child-info")} onTasks={() => onModeChange("tasks")} /> : null}{mode === "child-info" && child ? <ChildInformationWorkspace child={child} onBack={() => onModeChange("child")} /> : null}</section>;
}

function HomeActions({ connections, onModeChange }: Pick<ActionPanelProps, "connections" | "onModeChange">) {
  return <><h1><span>mom.</span><em>life</em></h1><div className={styles.primaryActions}><button className={styles.ask} onClick={() => onModeChange("ask")} type="button"><SquarePen /><span>Ask</span></button><button className={styles.tasks} onClick={() => onModeChange("tasks")} type="button"><ClipboardCheck /><span>Tasks</span></button></div>{connections.loaded ? <UtilityNav connectedIds={connections.connectedIds} onAdd={() => onModeChange("plugins")} /> : null}</>;
}
