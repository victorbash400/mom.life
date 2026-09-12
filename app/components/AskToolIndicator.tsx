import { CalendarClock, ClipboardList, ListTodo, SquareTerminal, Users, type LucideIcon } from "lucide-react";
import type { ToolMessage } from "../types/chat";
import styles from "./AskToolIndicator.module.css";

const icons: Record<string, LucideIcon> = {
  get_current_datetime: CalendarClock,
  get_family_context: Users,
  list_goal_tasks: ListTodo,
  create_family_goal: ClipboardList,
  revise_goal_plan: ListTodo,
};

export function AskToolIndicator({ item }: { item: ToolMessage }) {
  const Icon = icons[item.name] ?? SquareTerminal;
  return <span className={styles.tool} data-status={item.status} aria-label={`${item.name.replaceAll("_", " ")}: ${item.status}`}><Icon aria-hidden="true" size={14} /><strong>{item.name.replaceAll("_", " ")}</strong></span>;
}
