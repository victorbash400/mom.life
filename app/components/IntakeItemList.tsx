import type { IncomingItem } from "../types/intake";
import { IntakeItemRow } from "./IntakeItemRow";
import styles from "./IntakeItemList.module.css";

export function IntakeItemList({ items, selectedId, onSelect, onDelete }: { items: IncomingItem[]; selectedId?: string; onSelect: (id: string) => void; onDelete: (id: string) => Promise<void> }) {
  return <section aria-label="Incoming items" className={styles.list}>{items.map((item) => <IntakeItemRow item={item} key={item.id} onDelete={onDelete} onSelect={() => onSelect(item.id)} selected={item.id === selectedId} />)}</section>;
}
