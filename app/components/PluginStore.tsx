"use client";

import { ArrowLeft, Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";

import { toolDirectory, toolGroups, type ToolDefinition } from "../data/toolDirectory";
import type { useToolConnections } from "../hooks/useToolConnections";
import { ConnectedToolSection } from "./ConnectedToolSection";
import { GoogleWorkspaceSection } from "./GoogleWorkspaceSection";
import { PluginStoreGroup } from "./PluginStoreGroup";
import styles from "./PluginStore.module.css";

type Connections = ReturnType<typeof useToolConnections>;

export function PluginStore({ connections, onBack }: { connections: Connections; onBack: () => void }) {
  const [view, setView] = useState<"plugins" | "directory">("plugins");
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState<string>();
  const [actionError, setActionError] = useState<string>();
  const deferred = useDeferredValue(query.trim().toLocaleLowerCase());
  const states = useMemo(() => new Map(connections.states.map((state) => [state.id, state])), [connections.states]);
  const entries = useMemo(() => toolDirectory.filter((tool) => !deferred || `${tool.name} ${tool.description}`.toLocaleLowerCase().includes(deferred)), [deferred]);
  const workspace = entries.find((tool) => tool.id === "google-workspace" && states.get(tool.id)?.installed);
  const installed = entries.filter((tool) => tool.id !== "google-workspace" && states.get(tool.id)?.installed);

  async function run(tool: ToolDefinition, action: () => Promise<void>) {
    setBusyId(tool.id);
    setActionError(undefined);
    try { await action(); }
    catch (reason) { setActionError(reason instanceof Error ? reason.message : `Could not update ${tool.name}.`); }
    finally { setBusyId(undefined); }
  }

  function changeView(next: "plugins" | "directory") {
    setQuery("");
    setActionError(undefined);
    setView(next);
  }

  if (!connections.loaded) return <p className={styles.loading}>Loading plugins…</p>;

  return <section aria-label="Plugins" className={styles.viewport}><div className={styles.store} data-view={view}>
    <header className={styles.heading}><span><button aria-label="Back to home" className={styles.back} onClick={onBack} type="button"><ArrowLeft aria-hidden="true" /></button><h1>{view === "plugins" ? "Plugins" : "Plugin directory"}</h1></span><button className={styles.browse} onClick={() => changeView(view === "plugins" ? "directory" : "plugins")} type="button">{view === "plugins" ? "Browse directory" : "Back to plugins"}</button></header>
    <label className={styles.search}><Search aria-hidden="true" /><input aria-label="Search plugins" onChange={(event) => setQuery(event.target.value)} placeholder="Search plugins" type="search" value={query} /></label>
    {connections.error || actionError ? <p className={styles.error} role="alert">{actionError || connections.error}</p> : null}
    <div className={styles.content}>{view === "plugins" ? <>
      {workspace && states.get(workspace.id) ? <GoogleWorkspaceSection busy={busyId === workspace.id} connections={connections} onRun={(action) => run(workspace, action)} state={states.get(workspace.id)!} /> : null}
      {installed.map((tool) => {
        const state = states.get(tool.id);
        return state ? <ConnectedToolSection busy={busyId === tool.id} connections={connections} key={tool.id} onRun={(action) => run(tool, action)} state={state} tool={tool} /> : null;
      })}
      {!installed.length && !workspace ? <p className={styles.empty}>No plugins added. Browse the directory to add one.</p> : null}
    </> : toolGroups.map((group) => <PluginStoreGroup busyId={busyId} group={group} key={group} onAdd={(tool) => run(tool, () => connections.connect(tool.id))} states={states} tools={entries.filter((tool) => tool.group === group)} />)}</div>
  </div></section>;
}
