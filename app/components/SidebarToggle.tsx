import { PanelLeft } from "lucide-react";
import styles from "./SidebarToggle.module.css";

export function SidebarToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return <button className={styles.toggle} data-open={open} type="button" aria-label={open ? "Close sidebar" : "Open sidebar"} aria-expanded={open} onClick={onToggle}><PanelLeft aria-hidden="true" /></button>;
}
