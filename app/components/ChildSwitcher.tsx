"use client";

import { useState } from "react";
import { children } from "../data/dashboard";
import styles from "./ChildSwitcher.module.css";

export function ChildSwitcher() {
  const [selectedId, setSelectedId] = useState(children[0].id);
  const displayOrder = [children[1], children[0], children[2]];
  return <div className={styles.switcher} aria-label="Choose a child">{displayOrder.map((child) => <button key={child.id} type="button" aria-label={child.name} aria-pressed={selectedId === child.id} onClick={() => setSelectedId(child.id)}><span style={{ backgroundPosition: child.avatarPosition }} /></button>)}</div>;
}
