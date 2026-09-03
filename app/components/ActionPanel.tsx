import { ClipboardCheck, MessageSquare } from "lucide-react";
import { OrganicPanelSurface } from "./OrganicPanelSurface";
import { UtilityNav } from "./UtilityNav";
import styles from "./ActionPanel.module.css";

export function ActionPanel() {
  return <section className={styles.panel}><OrganicPanelSurface /><h1><span>mom.</span><em>life</em></h1><div className={styles.primaryActions}><button className={styles.chat} type="button"><MessageSquare /><span>Chat</span></button><button className={styles.tasks} type="button"><ClipboardCheck /><span>Tasks</span></button></div><UtilityNav /></section>;
}
