import { Plus } from "lucide-react";
import { toolDirectory } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./UtilityNav.module.css";
export function UtilityNav({ connectedIds, onAdd }: { connectedIds: string[]; onAdd: () => void }) { const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id)); if (!connected.length) return <button className={styles.add} onClick={onAdd} type="button"><Plus /><span>Add connections</span></button>; return <nav className={styles.nav} aria-label="Connected tools">{connected.map((tool) => <button aria-label={tool.name} key={tool.id} title={tool.name} type="button"><ToolIcon tool={tool} /></button>)}<button aria-label="Add connections" onClick={onAdd} title="Add connections" type="button"><Plus /></button></nav>; }
