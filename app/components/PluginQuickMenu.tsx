"use client";
import { ArrowRight, Plus, X } from "lucide-react";
import { toolDirectory } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./PluginQuickMenu.module.css";
export function PluginQuickMenu({ connectedIds, onClose, onDisconnect, onStore }: { connectedIds: string[]; onClose: () => void; onDisconnect: (id: string) => void; onStore: () => void }) {
  const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id));
  return <aside aria-label="Connections" className={styles.menu}><header><strong>Connections</strong><button aria-label="Close connections" onClick={onClose} type="button"><X /></button></header>{connected.length ? <div className={styles.tools}>{connected.map((tool) => <article key={tool.id}><ToolIcon size="small" tool={tool} /><span><strong>{tool.name}</strong><small>Connected</small></span><button aria-label={`Disconnect ${tool.name}`} onClick={() => onDisconnect(tool.id)} type="button">Disconnect</button></article>)}</div> : <div className={styles.empty}><span><Plus /></span><strong>No connections yet</strong><p>Add tools for calendars, email, documents, and household planning.</p></div>}<button className={styles.store} onClick={onStore} type="button">Go to store<ArrowRight /></button></aside>;
}
