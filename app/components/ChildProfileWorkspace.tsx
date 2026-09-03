import { ClipboardCheck, Database } from "lucide-react";
import type { ChildProfile } from "../types/dashboard";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./ChildProfileWorkspace.module.css";
export function ChildProfileWorkspace({ child, onBack, onInformation, onTasks }: { child: ChildProfile; onBack: () => void; onInformation: () => void; onTasks: () => void }) { return <div className={styles.profile}><WorkspaceHeader title="" onClose={onBack} /><h1>{child.name}</h1><div className={styles.cards}><button onClick={onTasks} type="button"><span><ClipboardCheck /></span><strong>Tasks</strong></button><button onClick={onInformation} type="button"><span><Database /></span><strong>Information</strong></button></div></div>; }
