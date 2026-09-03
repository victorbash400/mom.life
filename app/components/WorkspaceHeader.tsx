import { ArrowLeft } from "lucide-react";
import styles from "./WorkspaceHeader.module.css";

export function WorkspaceHeader({ title, onClose, action }: { title: string; onClose: () => void; action?: React.ReactNode }) {
  return <header className={styles.header}><button aria-label="Back to home" className={styles.back} onClick={onClose} type="button"><ArrowLeft /></button><strong>{title}</strong>{action}</header>;
}
