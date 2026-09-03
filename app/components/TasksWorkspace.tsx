"use client";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useFamilyTasks } from "../hooks/useFamilyTasks";
import { CreateTaskDialog } from "./CreateTaskDialog";
import { TaskControls, type TaskFilter } from "./TaskControls";
import { TaskList } from "./TaskList";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./TasksWorkspace.module.css";
export function TasksWorkspace({ onClose }: { onClose: () => void }) {
  const { createTask, deleteTask, error, loaded, setTaskStatus, tasks } = useFamilyTasks(); const [status, setStatus] = useState<TaskFilter>("all"); const [child, setChild] = useState("all"); const [sort, setSort] = useState("newest"); const [creating, setCreating] = useState(false);
  const visible = useMemo(() => tasks.filter((task) => (status === "all" || task.status === status) && (child === "all" || task.child_id === child)).sort((left, right) => sort === "oldest" ? left.created_at.localeCompare(right.created_at) : sort === "child" ? left.child_id.localeCompare(right.child_id) : right.created_at.localeCompare(left.created_at)), [child, sort, status, tasks]);
  const title = status === "all" ? "All tasks" : `${status[0].toUpperCase()}${status.slice(1)} tasks`;
  return <div className={styles.workspace}><WorkspaceHeader title="Tasks" subtitle="Tasks across your family" onClose={onClose} action={<button className={styles.newTask} onClick={() => setCreating(true)} type="button"><Plus />New Task</button>} /><TaskControls child={child} filter={status} onChildChange={setChild} onFilterChange={setStatus} onSortChange={setSort} sort={sort} />{error ? <p className={styles.error} role="alert">{error}</p> : null}{loaded ? <TaskList onDelete={deleteTask} onStatusChange={setTaskStatus} tasks={visible} title={title} /> : null}<CreateTaskDialog onCancel={() => setCreating(false)} onSubmit={async (taskChild, text) => { await createTask(taskChild, text); setCreating(false); setStatus("active"); }} open={creating} /></div>;
}
