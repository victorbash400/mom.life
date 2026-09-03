import type { ReactNode } from "react";
import styles from "./SettingsRow.module.css";
export function SettingsRow({ title, description, control }: { title: string; description?: string; control: ReactNode }) { return <article className={styles.row}><span><strong>{title}</strong>{description ? <small>{description}</small> : null}</span>{control}</article>; }
