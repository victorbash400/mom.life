import { ArrowLeft } from "lucide-react";
import styles from "./WorkspaceHeader.module.css";

export function WorkspaceHeader({ title, subtitle, onClose, action }: { title: string; subtitle: string; onClose: () => void; action?: React.ReactNode }) {
  return <header className={styles.header}><button aria-label="Back to home" onClick={onClose} type="button"><ArrowLeft /></button><span><strong>{title}</strong><small>{subtitle}</small></span>{action}</header>;
}
