import { useFamily } from "./FamilyProvider";
import { SignOutButton } from "./auth/SignOutButton";
import { ClipboardCheck, Settings } from "lucide-react";
import { PinkFolderIcon } from "./PinkFolderIcon";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./ParentProfileWorkspace.module.css";

export function ParentProfileWorkspace({ onBack, onInformation, onSettings, onTasks }: { onBack: () => void; onInformation: () => void; onSettings: () => void; onTasks: () => void }) {
  const { family: { parent } } = useFamily();
  return <section className={styles.profile}><WorkspaceHeader title="" onClose={onBack} /><h1>{parent.name}</h1><div className={styles.cards}><button onClick={onTasks} type="button"><ClipboardCheck /><strong>Tasks</strong></button><button onClick={onInformation} type="button"><PinkFolderIcon /><strong>Information</strong></button><button onClick={onSettings} type="button"><Settings /><strong>Settings</strong></button></div><SignOutButton /></section>;
}
