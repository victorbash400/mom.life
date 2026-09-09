import { toolDirectory } from "../data/toolDirectory";
import { ConnectedToolIcon } from "./ConnectedToolIcon";
import styles from "./UtilityNav.module.css";
export function UtilityNav({ connectedIds }: { connectedIds: string[] }) { const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id)); if (!connected.length) return null; return <nav className={styles.nav} aria-label="Connected tools">{connected.map((tool) => <button aria-label={tool.name} key={tool.id} title={tool.name} type="button"><ConnectedToolIcon tool={tool} /></button>)}</nav>; }
