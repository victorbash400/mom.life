import { ArrowLeft } from "lucide-react";
import styles from "./WorkspaceHeader.module.css";

export function WorkspaceHeader({ title, onClose, action, backLabel = "Back to home" }: { title: string; onClose: () => void; action?: React.ReactNode; backLabel?: string }) {
  return <header className={styles.header}><button aria-label={backLabel} className={styles.back} onClick={onClose} type="button"><ArrowLeft /></button><strong>{title}</strong>{action}</header>;
}
