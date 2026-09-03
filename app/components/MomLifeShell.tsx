"use client";

import { useState } from "react";
import type { ViewId } from "../types/dashboard";
import { Sidebar } from "./Sidebar";
import { SidebarToggle } from "./SidebarToggle";
import styles from "./MomLifeShell.module.css";

export function MomLifeShell() {
  const [activeView, setActiveView] = useState<ViewId>("today");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null);
  return (
    <main className={styles.shell}>
      <SidebarToggle open={sidebarOpen} onToggle={() => setSidebarOpen((value) => !value)} />
      <Sidebar activeView={activeView} expanded={sidebarOpen} selectedChildId={selectedChildId} onSelectChild={setSelectedChildId} onSelectView={setActiveView} />
    </main>
  );
}
