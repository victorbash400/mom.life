import { ShieldCheck } from "lucide-react";
import styles from "./SecurityEmptyState.module.css";

export function SecurityEmptyState() { return <section className={styles.empty}><ShieldCheck aria-hidden="true" /><strong>No security alerts</strong></section>; }
