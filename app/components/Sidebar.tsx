import { CalendarDays, CheckCheck, CircleHelp, HeartHandshake, House, Link2, Settings2 } from "lucide-react";
import type { ViewId } from "../types/dashboard";
import { children } from "../data/dashboard";
import { FamilyAvatar } from "./FamilyAvatar";
import styles from "./Sidebar.module.css";

const items: { id: ViewId; label: string; icon: typeof House; count?: number }[] = [
  { id: "today", label: "Today", icon: House },
  { id: "needs-you", label: "Needs you", icon: CircleHelp, count: 3 },
  { id: "handled", label: "Handled", icon: CheckCheck },
  { id: "calendar", label: "Calendar", icon: CalendarDays },
  { id: "memory", label: "Memory", icon: HeartHandshake },
  { id: "connections", label: "Connections", icon: Link2 },
];

interface SidebarProps {
  activeView: ViewId;
  expanded: boolean;
  selectedChildId: string | null;
  onSelectChild: (id: string | null) => void;
  onSelectView: (id: ViewId) => void;
}

export function Sidebar({ activeView, expanded, selectedChildId, onSelectChild, onSelectView }: SidebarProps) {
  return (
    <nav className={styles.rail} data-expanded={expanded} aria-label="mom.life controls">
      <span className={styles.title}>mom.life</span>
      <div className={styles.actions}>
        {items.map(({ id, label, icon: Icon, count }) => (
          <button type="button" key={id} aria-label={label} aria-pressed={activeView === id} title={label} onClick={() => onSelectView(id)}>
            <Icon aria-hidden="true" /><span>{label}</span>{count ? <b>{count}</b> : null}
          </button>
        ))}
      </div>
      <div className={styles.children} aria-label="Children">
        {children.map((child) => (
          <button type="button" key={child.id} aria-label={child.name} aria-pressed={selectedChildId === child.id} title={child.name} onClick={() => onSelectChild(selectedChildId === child.id ? null : child.id)}>
            <FamilyAvatar name={child.name} position={child.avatarPosition} /><span>{child.name}</span>
          </button>
        ))}
      </div>
      <button className={styles.settings} type="button" aria-label="Settings" title="Settings"><Settings2 aria-hidden="true" /><span>Settings</span></button>
    </nav>
  );
}
