import { ClipboardCheck, SquarePen } from "lucide-react";
import type { PanelMode } from "./MomLifeShell";
import { AskWorkspace } from "./AskWorkspace";
import { OrganicPanelSurface } from "./OrganicPanelSurface";
import { TasksWorkspace } from "./TasksWorkspace";
import { UtilityNav } from "./UtilityNav";
import styles from "./ActionPanel.module.css";

type ActionPanelProps = { mode: PanelMode; onModeChange: (mode: PanelMode) => void };

export function ActionPanel({ mode, onModeChange }: ActionPanelProps) {
  return <section className={styles.panel} data-mode={mode}><OrganicPanelSurface mode={mode} />{mode === "home" ? <HomeActions onModeChange={onModeChange} /> : null}{mode === "ask" ? <AskWorkspace onClose={() => onModeChange("home")} /> : null}{mode === "tasks" ? <TasksWorkspace onClose={() => onModeChange("home")} /> : null}</section>;
}

function HomeActions({ onModeChange }: Pick<ActionPanelProps, "onModeChange">) {
  return <><h1><span>mom.</span><em>life</em></h1><div className={styles.primaryActions}><button className={styles.ask} onClick={() => onModeChange("ask")} type="button"><SquarePen /><span>Ask</span></button><button className={styles.tasks} onClick={() => onModeChange("tasks")} type="button"><ClipboardCheck /><span>Tasks</span></button></div><UtilityNav /></>;
}
