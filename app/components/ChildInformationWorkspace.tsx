import { CalendarDays, HeartPulse, Ruler } from "lucide-react";
import type { ChildProfile } from "../types/dashboard";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./ChildInformationWorkspace.module.css";
export function ChildInformationWorkspace({ child, onBack }: { child: ChildProfile; onBack: () => void }) { return <div className={styles.information}><WorkspaceHeader backLabel={`Back to ${child.name}`} title={`${child.name} · Information`} onClose={onBack} /><div className={styles.grid}><article><span><CalendarDays /></span><small>Age</small><strong>{child.age}</strong></article><article><span><HeartPulse /></span><small>Health</small><strong>No information yet</strong></article><article><span><Ruler /></span><small>Measurements</small><strong>No information yet</strong></article></div></div>; }
