"use client";
import { Check, ChevronDown, Pause, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FamilyTask } from "../hooks/useFamilyTasks";
import styles from "./TaskRow.module.css";
export function TaskRow({ task, onDelete, onStatusChange }: { task: FamilyTask; onDelete: (id: string) => Promise<void>; onStatusChange: (id: string, status: FamilyTask["status"]) => Promise<void> }) {
  const [expanded, setExpanded] = useState(false);
  return <article className={styles.row} data-expanded={expanded} data-state={task.status}><button aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} type="button"><span className={styles.marker}>{task.status === "completed" ? <Check /> : task.status === "paused" ? <Pause /> : null}</span><span className={styles.copy}><strong>{task.text}</strong></span><ChevronDown className={styles.chevron} /></button><section className={styles.reveal} aria-hidden={!expanded}><span><footer><small>{childName(task.child_id)}</small><div>{task.status !== "completed" ? <button aria-label={task.status === "active" ? "Pause task" : "Resume task"} onClick={() => void onStatusChange(task.id, task.status === "active" ? "paused" : "active")} type="button">{task.status === "active" ? <Pause /> : <Play />}</button> : null}<button aria-label="Delete task" onClick={() => void onDelete(task.id)} type="button"><Trash2 /></button></div></footer></span></section></article>;
}
function childName(id: string) { if (id === "amina") return "Amina"; if (id === "noah") return "Noah"; if (id === "lila") return "Lila"; return "All Children"; }
