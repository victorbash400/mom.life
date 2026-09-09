import { siGoogle, siGoogleclassroom, siGooglemaps, siNotion, siTodoist, type SimpleIcon } from "simple-icons";
import type { ToolDefinition } from "../data/toolDirectory";
import styles from "./ConnectedToolIcon.module.css";

const marks: Partial<Record<string, SimpleIcon>> = {
  "google-workspace": siGoogle,
  "google-maps": siGooglemaps,
  "google-classroom": siGoogleclassroom,
  notion: siNotion,
  todoist: siTodoist,
};

export function ConnectedToolIcon({ tool }: { tool: ToolDefinition }) {
  const mark = marks[tool.id];
  if (mark) return <svg aria-hidden="true" className={styles.mark} viewBox="0 0 24 24"><path d={mark.path} /></svg>;
  if (tool.id === "canva") return <span aria-hidden="true" className={styles.canva}>C</span>;
  const Icon = tool.icon;
  return <Icon aria-hidden="true" className={styles.fallback} />;
}
