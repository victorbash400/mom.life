"use client";

import { ListFilter, UserRound } from "lucide-react";
import { useFamily } from "./FamilyProvider";
import { TaskPicker } from "./TaskPicker";
import styles from "./TaskControls.module.css";

export type TaskFilter = "all" | "active" | "paused" | "completed";
const filters: { key: TaskFilter; label: string }[] = [{ key: "all", label: "All" }, { key: "active", label: "Active" }, { key: "paused", label: "Paused" }, { key: "completed", label: "Completed" }];

export function TaskControls({ child, filter, sort, onChildChange, onFilterChange, onSortChange }: { child: string; filter: TaskFilter; sort: string; onChildChange: (child: string) => void; onFilterChange: (filter: TaskFilter) => void; onSortChange: (sort: string) => void }) {
  const { family: { children } } = useFamily();
  const childOptions = [{ label: "All Children", value: "all" }, ...children.map(({ id, name }) => ({ label: name, value: id }))];
  return <div className={styles.controls}><nav aria-label="Task status">{filters.map(({ key, label }) => <button aria-current={filter === key ? "page" : undefined} key={key} onClick={() => onFilterChange(key)} type="button">{label}</button>)}</nav><span><TaskPicker icon={UserRound} label="Filter tasks by child" onChange={onChildChange} options={childOptions} value={child} /><TaskPicker icon={ListFilter} label="Sort tasks" onChange={onSortChange} options={[{ label: "Newest", value: "newest" }, { label: "Oldest", value: "oldest" }, { label: "Child", value: "child" }]} value={sort} /></span></div>;
}
