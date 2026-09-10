import { toolDirectory } from "../data/toolDirectory";
import { ConnectedToolIcon } from "./ConnectedToolIcon";
import styles from "./UtilityNav.module.css";
export function UtilityNav({ connectedIds }: { connectedIds: string[] }) { const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id)); if (!connected.length) return null; return <nav className={styles.nav} aria-label="Connected tools">{connected.map((tool) => <button aria-label={tool.name} data-tooltip={tool.name} key={tool.id} type="button"><ConnectedToolIcon tool={tool} /></button>)}</nav>; }
