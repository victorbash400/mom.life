import { ListFilter, UserRound } from "lucide-react";
import styles from "./TaskControls.module.css";

export type TaskFilter = "all" | "active" | "paused" | "completed";
const filters: { key: TaskFilter; label: string }[] = [{ key: "all", label: "All" }, { key: "active", label: "Active" }, { key: "paused", label: "Paused" }, { key: "completed", label: "Completed" }];

export function TaskControls({ child, filter, onChildChange, onFilterChange }: { child: string; filter: TaskFilter; onChildChange: (child: string) => void; onFilterChange: (filter: TaskFilter) => void }) {
  return <div className={styles.controls}><nav aria-label="Task status">{filters.map(({ key, label }) => <button aria-current={filter === key ? "page" : undefined} key={key} onClick={() => onFilterChange(key)} type="button">{label}</button>)}</nav><span><label><UserRound /><select aria-label="Filter tasks by child" onChange={(event) => onChildChange(event.target.value)} value={child}><option value="all">All Children</option><option value="amina">Amina</option><option value="noah">Noah</option><option value="lila">Lila</option></select></label><label><ListFilter /><select aria-label="Sort tasks" defaultValue="newest"><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="child">Child</option></select></label></span></div>;
}
