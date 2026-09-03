"use client";

import { children } from "../data/dashboard";
import styles from "./ChildSwitcher.module.css";

export function ChildSwitcher({ focused, selectedId, onSelect }: { focused: boolean; selectedId?: string; onSelect: (id: string) => void }) {
  const displayOrder = [children[1], children[0], children[2]];
  return <div className={styles.switcher} data-focused={focused} aria-label="Choose a child">{displayOrder.map((child) => <button key={child.id} type="button" aria-label={child.name} aria-pressed={selectedId === child.id} onClick={() => onSelect(child.id)}><span style={{ backgroundPosition: child.avatarPosition }} /></button>)}</div>;
}
