import type { FamilyTask } from "../hooks/useFamilyTasks";
import { TaskRow } from "./TaskRow";
import styles from "./TaskList.module.css";

export function TaskList({ tasks, title, onDelete, onStatusChange, onRevise, onAnswer }: { onRevise: (id: string, instruction: string) => Promise<void>; onAnswer: (id: string, questionId: string, answer: string, approved: boolean) => Promise<void>; tasks: FamilyTask[]; title: string; onDelete: (id: string) => Promise<void>; onStatusChange: (id: string, status: FamilyTask["status"]) => Promise<void> }) {
  return <section className={styles.panel}><header><span>{title}</span><small>{tasks.length}</small></header><div className={styles.sheet}>{tasks.length ? tasks.map((task) => <TaskRow onRevise={onRevise} onAnswer={onAnswer} key={task.id} onDelete={onDelete} onStatusChange={onStatusChange} task={task} />) : <p className={styles.empty}>Tasks in this view will appear here</p>}</div></section>;
}
