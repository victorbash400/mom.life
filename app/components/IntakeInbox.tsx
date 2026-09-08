import type { IncomingItem } from "../types/intake";
import { IntakeAgentActivity } from "./IntakeAgentActivity";
import { IntakeDetail } from "./IntakeDetail";
import { IntakeEmptyState } from "./IntakeEmptyState";
import { IntakeItemList } from "./IntakeItemList";
import styles from "./IntakeInbox.module.css";

export function IntakeInbox({ items, selectedId, onSelect, onRetry, onDelete }: { items: IncomingItem[]; selectedId?: string; onSelect: (id: string) => void; onRetry: (id: string) => Promise<void>; onDelete: (id: string) => Promise<void> }) {
  const selected = items.find((item) => item.id === selectedId) ?? items[0];
  return <section className={styles.inbox} data-empty={!items.length}>{items.length ? <><IntakeItemList items={items} onDelete={onDelete} onSelect={onSelect} selectedId={selected?.id} />{selected ? <><IntakeDetail item={selected} /><IntakeAgentActivity item={selected} onRetry={onRetry} /></> : null}</> : <IntakeEmptyState />}</section>;
}
