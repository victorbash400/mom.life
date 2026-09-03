"use client";

import { useState } from "react";
import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import styles from "./MomLifeShell.module.css";

export type PanelMode = "home" | "ask" | "tasks";

export function MomLifeShell() {
  const [mode, setMode] = useState<PanelMode>("home");
  return <main className={styles.shell} data-mode={mode}><AppHeader /><ChildSwitcher /><ActionPanel mode={mode} onModeChange={setMode} /></main>;
}
