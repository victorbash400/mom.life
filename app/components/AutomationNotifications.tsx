import { useState } from "react";
import { Bell, Check } from "lucide-react";
import type { AutomationNotification } from "../types/automations";
import styles from "./AutomationList.module.css";
export function AutomationNotifications({ items, change }: { items: AutomationNotification[]; change: (id: string, method: string) => Promise<void> }) {
  const [error, setError] = useState("");
  async function read(id: string) { try { await change(`notifications/${id}/read`, "POST"); setError(""); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not mark notification read."); } }
  return <>{error && <p role="alert">{error}</p>}<ul className={styles.notifications}>{items.filter((item) => !item.read_at).map((item) => <li key={item.id}><Bell aria-hidden="true" size={14} /><p>{item.message}</p><button aria-label="Mark notification read" onClick={() => void read(item.id)} type="button"><Check size={14} /></button></li>)}</ul></>;
}
