"use client";
import { Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { toolDirectory, toolGroups, type ToolDefinition } from "../data/toolDirectory";
import { ConnectionDialog } from "./ConnectionDialog";
import { PluginStoreGroup } from "./PluginStoreGroup";
import { ToolIcon } from "./ToolIcon";
import { WorkspaceHeader } from "./WorkspaceHeader";
import type { useToolConnections } from "../hooks/useToolConnections";
import { SkillsLibrary } from "./SkillsLibrary";
import styles from "./PluginStore.module.css";
export function PluginStore({ connections, onBack }: { connections: ReturnType<typeof useToolConnections>; onBack: () => void }) {
  const { connectedIds } = connections;
  const [view, setView] = useState("connections");
  const [query, setQuery] = useState(""); const [selected, setSelected] = useState<ToolDefinition>(); const deferred = useDeferredValue(query.trim().toLowerCase()); const entries = useMemo(() => toolDirectory.filter((tool) => !deferred || `${tool.name} ${tool.description}`.toLowerCase().includes(deferred)), [deferred]); const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id));
  return <div className={styles.store}><WorkspaceHeader title="Connections" onClose={onBack} /><nav className={styles.tabs}><button type="button" aria-pressed={view === "connections"} onClick={() => setView("connections")}>Connections</button><button type="button" aria-pressed={view === "skills"} onClick={() => setView("skills")}>Skills</button></nav>{view === "skills" ? <SkillsLibrary /> : <><label className={styles.search}><Search /><input aria-label="Search connections" onChange={(event) => setQuery(event.target.value)} placeholder="Search connections" type="search" value={query} /></label>{connected.length ? <section className={styles.connected}><header><strong>Connected</strong><small>{connected.length}</small></header><div>{connected.map((tool) => <button aria-label={`Manage ${tool.name}`} key={tool.id} onClick={() => setSelected(tool)} title={`Manage ${tool.name}`} type="button"><ToolIcon tool={tool} /></button>)}</div></section> : null}<div className={styles.directory}>{toolGroups.map((group) => <PluginStoreGroup connectedIds={connectedIds} group={group} key={group} onAdd={setSelected} tools={entries.filter((tool) => tool.group === group)} />)}</div>{connections.error ? <p role="alert">{connections.error}</p> : null}<ConnectionDialog key={selected?.id} onCancel={() => setSelected(undefined)} connections={connections} tool={selected} /></>}</div>;
}
