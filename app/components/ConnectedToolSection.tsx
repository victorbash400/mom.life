"use client";

import { ChevronDown } from "lucide-react";

import type { ToolDefinition, ToolState } from "../data/toolDirectory";
import type { useToolConnections } from "../hooks/useToolConnections";
import { ToolIcon } from "./ToolIcon";
import styles from "./ConnectedToolSection.module.css";

type Connections = ReturnType<typeof useToolConnections>;

export function ConnectedToolSection({ busy, connections, onRun, state, tool}: { busy: boolean; connections: Connections; onRun: (action: () => Promise<void>) => Promise<void>; state: ToolState; tool: ToolDefinition }) {
  const simulated = state.connection_mode === "simulated";
  const connectLive = state.oauth_supported && !state.account_label ? () => connections.authorize(tool.id) : () => connections.validate(tool.id);
  return <section className={styles.section}>
    <h2>{tool.name}</h2>
    <details className={styles.plugin}>
      <summary><ToolIcon size="small" tool={tool} /><span className={styles.copy}><strong>{tool.description}</strong><small>{simulated ? "Simulator connected" : state.connected ? "Connected" : "Not connected"}</small></span><span className={state.connected ? styles.connected : styles.disconnected}>{simulated ? "Simulator" : state.connected ? "Connected" : "Not connected"}</span><ChevronDown aria-hidden="true" className={styles.chevron} /></summary>
      <section aria-label={`${tool.name} connection settings`} className={styles.settings}>
        <header><span><strong>Connection</strong><small>{simulated ? `${tool.name} is using simulator data` : state.connected ? `${tool.name} is connected` : `Connect ${tool.name} to mom.life`}</small></span><span className={styles.actions}>{state.connected ? <button className={styles.disconnect} disabled={busy} onClick={() => void onRun(simulated ? () => connections.disconnectSimulation(tool.id) : () => connections.disconnect(tool.id))} type="button">Disconnect</button> : <><button className={styles.connect} disabled={busy || !state.connection_supported} onClick={() => void onRun(connectLive)} type="button">Connect</button>{state.simulation_supported ? <button className={styles.simulate} disabled={busy} onClick={() => void onRun(() => connections.simulate(tool.id))} type="button">Use simulator</button> : null}</>}</span></header>
        {state.connected ? <fieldset><legend>Permissions</legend>{state.permissions.map((permission) => <label key={permission.id}><input checked={permission.enabled} disabled={busy} onChange={(event) => void onRun(() => connections.permission(tool.id, permission.id, event.target.checked))} type="checkbox" />{permission.name}</label>)}</fieldset> : null}
        <footer><button disabled={busy} onClick={() => void onRun(() => connections.disconnect(tool.id))} type="button">Remove plugin</button></footer>
      </section>
    </details>
  </section>;
}
