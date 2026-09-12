"use client";
import { childAvatarStyle } from "./ChildAvatar";

import { useFamily } from "./FamilyProvider";
import styles from "./ChildSwitcher.module.css";

export function ChildSwitcher({ focused, selectedId, onSelect }: { focused: boolean; selectedId?: string; onSelect: (id: string) => void }) {
  const { family: { children } } = useFamily();
  const displayOrder = children;
  return <div className={styles.switcher} data-focused={focused} aria-label="Choose a child">{displayOrder.map((child) => <button key={child.id} type="button" aria-label={child.name} aria-pressed={selectedId === child.id} data-tooltip={child.name} onClick={() => onSelect(child.id)}><span style={childAvatarStyle(child)} /></button>)}</div>;
}
