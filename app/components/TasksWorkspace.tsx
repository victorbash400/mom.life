"use client";
import { AutomationList } from "./AutomationList";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useFamilyTasks } from "../hooks/useFamilyTasks";
import { CreateTaskDialog } from "./CreateTaskDialog";
import { LoadingIndicator } from "./LoadingIndicator";
import { TaskControls, type TaskFilter } from "./TaskControls";
import { TaskList } from "./TaskList";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./TasksWorkspace.module.css";
export function TasksWorkspace({ initialChild = "all", onClose }: { initialChild?: string; onClose: () => void }) {
  const { createTask, deleteTask, error, loaded, setTaskStatus, tasks, reviseTask, answerQuestion } = useFamilyTasks(); const [status, setStatus] = useState<TaskFilter>("all"); const [childFilter, setChildFilter] = useState({ source: initialChild, value: initialChild }); const [sort, setSort] = useState("newest"); const [creating, setCreating] = useState(false);
  const child = childFilter.source === initialChild ? childFilter.value : initialChild;
  const visible = useMemo(() => tasks.filter((task) => (status === "all" || task.status === status) && (child === "all" || task.child_id === child)).sort((left, right) => sort === "oldest" ? left.created_at.localeCompare(right.created_at) : sort === "child" ? left.child_id.localeCompare(right.child_id) : right.created_at.localeCompare(left.created_at)), [child, sort, status, tasks]);
  const title = status === "all" ? "All tasks" : `${status[0].toUpperCase()}${status.slice(1)} tasks`;
  return <div className={styles.workspace}><WorkspaceHeader backLabel={initialChild === "all" ? "Back to home" : "Back to child profile"} title="Tasks" onClose={onClose} action={<button className={styles.newTask} onClick={() => setCreating(true)} type="button"><Plus />New Task</button>} /><TaskControls child={child} filter={status} onChildChange={(value) => setChildFilter({ source: initialChild, value })} onFilterChange={setStatus} onSortChange={setSort} sort={sort} />{error ? <p className={styles.error} role="alert">{error}</p> : null}{status === "automations" ? <AutomationList child={child} /> : loaded ? <TaskList onRevise={reviseTask} onAnswer={answerQuestion} onDelete={deleteTask} onStatusChange={setTaskStatus} tasks={visible} title={title} /> : !error ? <LoadingIndicator className={styles.loading} /> : null}<CreateTaskDialog initialChild={initialChild} onCancel={() => setCreating(false)} onSubmit={async (taskChild, text) => { await createTask(taskChild, text); setCreating(false); setStatus("active"); }} open={creating} /></div>;
}
