"use client";
import { Check, ChevronDown, Pause, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FamilyTask } from "../hooks/useFamilyTasks";
import { GoalTaskBoard } from "./GoalTaskBoard";
import { AssignmentDetails } from "./AssignmentDetails";
import { GoalQuestion } from "./GoalQuestion";
import { GoalRevision } from "./GoalRevision";
import styles from "./TaskRow.module.css";
export function TaskRow({ task, onDelete, onStatusChange, onRevise, onAnswer }: { onRevise: (id: string, instruction: string) => Promise<void>; onAnswer: (id: string, questionId: string, answer: string, approved: boolean) => Promise<void>; task: FamilyTask; onDelete: (id: string) => Promise<void>; onStatusChange: (id: string, status: FamilyTask["status"]) => Promise<void> }) {
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string>();
  async function act(action: () => Promise<void>) { try { await action(); setError(undefined); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update task."); } }
  return <article className={styles.row} data-expanded={expanded} data-state={task.status}><button aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} type="button"><span className={styles.marker}>{task.status === "completed" ? <Check /> : task.status === "paused" ? <Pause /> : null}</span><span className={styles.copy}><strong>{task.text}</strong><small>{task.run_state.replaceAll("_", " ")}{task.current_step ? ` · ${task.current_step}` : ""}</small></span><ChevronDown className={styles.chevron} /></button><section className={styles.reveal} aria-hidden={!expanded} inert={!expanded}><span><div className={styles.details}><GoalTaskBoard task={task} />{task.assignments.map((assignment) => <AssignmentDetails key={assignment.id} assignment={assignment} activities={task.activities} />)}{task.questions.filter((question) => question.state === "open").map((question) => <GoalQuestion key={question.id} question={question} onAnswer={(answer, approved) => onAnswer(task.id, question.id, answer, approved)} />)}{task.status !== "completed" ? <GoalRevision onRevise={(instruction) => onRevise(task.id, instruction)} /> : null}{error ? <p role="alert">{error}</p> : null}</div><footer><small>{childName(task.child_id)}</small><div>{task.status !== "completed" ? <button aria-label={task.status === "active" ? "Pause task" : "Resume task"} onClick={() => void act(() => onStatusChange(task.id, task.status === "active" ? "paused" : "active"))} type="button">{task.status === "active" ? <Pause /> : <Play />}</button> : null}<button aria-label="Delete task" onClick={() => void act(() => onDelete(task.id))} type="button"><Trash2 /></button></div></footer></span></section></article>;
}
function childName(id: string) { if (id === "amina") return "Amina"; if (id === "noah") return "Noah"; if (id === "lila") return "Lila"; return "All Children"; }
