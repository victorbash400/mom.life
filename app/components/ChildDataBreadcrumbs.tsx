import { ChevronRight } from "lucide-react";
import styles from "./ChildDataBreadcrumbs.module.css";

export function ChildDataBreadcrumbs({ childName, folderName, onRoot }: { childName: string; folderName?: string; onRoot: () => void }) {
  return <nav aria-label="Breadcrumb" className={styles.breadcrumbs}><span className={styles.crumb}>{folderName ? <button onClick={onRoot} type="button">{childName}</button> : <strong aria-current="page">{childName}</strong>}</span>{folderName ? <span className={styles.crumb}><ChevronRight aria-hidden="true" /><strong aria-current="page">{folderName}</strong></span> : null}</nav>;
}
