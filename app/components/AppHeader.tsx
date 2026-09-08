import { Baby, Mail, Plug, ShieldCheck } from "lucide-react";
import Image from "next/image";

import { useFamily } from "./FamilyProvider";
import styles from "./AppHeader.module.css";

export function AppHeader({ incomingOpen, pluginsOpen, onChildrenOpen, onIncomingOpen, onProfileOpen, onPluginsToggle }: { incomingOpen: boolean; pluginsOpen: boolean; onChildrenOpen: () => void; onIncomingOpen: () => void; onProfileOpen: () => void; onPluginsToggle: () => void }) {
  const { family: { parent } } = useFamily();
  return <header className={styles.header}><button aria-label={`Open ${parent.name}'s profile`} className={styles.greeting} onClick={onProfileOpen} type="button"><Image src="/sarah-profile.png" alt={parent.name} width={44} height={44} priority /><span>Hi, {parent.name}</span></button><nav className={styles.actions} aria-label="Family controls"><button aria-label="Child Management" onClick={onChildrenOpen} title="Child Management" type="button"><Baby aria-hidden="true" /></button><button aria-expanded={pluginsOpen} onClick={onPluginsToggle} type="button" aria-label="Connections" title="Connections"><Plug aria-hidden="true" /></button><button aria-expanded={incomingOpen} aria-label="Incoming" onClick={onIncomingOpen} title="Incoming" type="button"><Mail aria-hidden="true" /></button><button aria-label="Safety" title="Safety" type="button"><ShieldCheck aria-hidden="true" /></button></nav></header>;
}
