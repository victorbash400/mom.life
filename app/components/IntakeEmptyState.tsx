import { Mail } from "lucide-react";
import styles from "./IntakeEmptyState.module.css";

export function IntakeEmptyState() {
  return <section className={styles.empty}><Mail aria-hidden="true" /><strong>No incoming items yet</strong></section>;
}
