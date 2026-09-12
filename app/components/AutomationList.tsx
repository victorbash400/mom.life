"use client";
import { useAutomations } from "../hooks/useAutomations";
import { useFamily } from "./FamilyProvider";
import { AutomationNotifications } from "./AutomationNotifications";
import { AutomationRow } from "./AutomationRow";
import styles from "./AutomationList.module.css";
export function AutomationList({ child }: { child: string }) {
  const { state, error, change } = useAutomations();
  const { family } = useFamily();
  const items = state?.automations.filter((item) => child === "all" || item.child_id === child) ?? [];
  return <section className={styles.list}>{error && <p role="alert">{error}</p>}{state && !state.scheduler_ready && <p role="status">AWS scheduler setup required</p>}{state && !state.events_connected && <p role="alert">Automation event subscription is disconnected.</p>}{state && <AutomationNotifications items={state.notifications} change={change} />}{state && !items.length && <p>Ask mom.life to monitor something or schedule a check.</p>}<ul>{items.map((item) => <AutomationRow key={item.id} item={item} change={change} childName={item.child_id === "all" ? "All children" : family.children.find((profile) => profile.id === item.child_id)?.name ?? item.child_id} />)}</ul></section>;
}
