"use client";
import { Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { toolDirectory, type ToolDefinition } from "../data/toolDirectory";
import { ConnectionDialog } from "./ConnectionDialog";
import { PluginStoreGroup } from "./PluginStoreGroup";
import { ToolIcon } from "./ToolIcon";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./PluginStore.module.css";
export function PluginStore({ connectedIds, onBack, onConnect, onDisconnect }: { connectedIds: string[]; onBack: () => void; onConnect: (id: string) => void; onDisconnect: (id: string) => void }) {
  const [query, setQuery] = useState(""); const [selected, setSelected] = useState<ToolDefinition>(); const deferred = useDeferredValue(query.trim().toLowerCase()); const entries = useMemo(() => toolDirectory.filter((tool) => !deferred || `${tool.name} ${tool.description}`.toLowerCase().includes(deferred)), [deferred]); const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id));
  return <div className={styles.store}><WorkspaceHeader title="Connections" onClose={onBack} /><label className={styles.search}><Search /><input aria-label="Search connections" onChange={(event) => setQuery(event.target.value)} placeholder="Search connections" type="search" value={query} /></label>{connected.length ? <section className={styles.connected}><header><strong>Connected</strong><small>{connected.length}</small></header><div>{connected.map((tool) => <button aria-label={`Manage ${tool.name}`} key={tool.id} onClick={() => onDisconnect(tool.id)} title={`Disconnect ${tool.name}`} type="button"><ToolIcon tool={tool} /></button>)}</div></section> : null}<div className={styles.directory}>{(["Family essentials", "Planning"] as const).map((group) => <PluginStoreGroup connectedIds={connectedIds} group={group} key={group} onAdd={setSelected} tools={entries.filter((tool) => tool.group === group)} />)}</div><ConnectionDialog onCancel={() => setSelected(undefined)} onConnect={(id) => { onConnect(id); setSelected(undefined); }} tool={selected} /></div>;
}
