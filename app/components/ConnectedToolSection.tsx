"use client";

import { ChevronDown } from "lucide-react";

import type { ToolDefinition, ToolState } from "../data/toolDirectory";
import type { useToolConnections } from "../hooks/useToolConnections";
import { ToolIcon } from "./ToolIcon";
import styles from "./ConnectedToolSection.module.css";

type Connections = ReturnType<typeof useToolConnections>;

export function ConnectedToolSection({ busy, connections, onRun, state, tool}: { busy: boolean; connections: Connections; onRun: (action: () => Promise<void>) => Promise<void>; state: ToolState; tool: ToolDefinition }) {
  return <section className={styles.section}>
    <h2>{tool.name}</h2>
    <details className={styles.plugin}>
      <summary><ToolIcon size="small" tool={tool} /><span className={styles.copy}><strong>{tool.description}</strong><small>{state.connected ? "Connected" : "Not connected"}</small></span><span className={state.connected ? styles.connected : styles.disconnected}>{state.connected ? "Connected" : "Not connected"}</span><ChevronDown aria-hidden="true" className={styles.chevron} /></summary>
      <section aria-label={`${tool.name} connection settings`} className={styles.settings}>
        <header><span><strong>Connection</strong><small>{state.connected ? `${tool.name} is connected` : `Connect ${tool.name} to mom.life`}</small></span><button className={state.connected ? styles.disconnect : styles.connect} disabled={busy || !state.connection_supported} onClick={() => void onRun(state.connected ? () => connections.disconnect(tool.id) : state.oauth_supported ? () => connections.authorize(tool.id) : () => connections.validate(tool.id))} type="button">{state.connected ? "Disconnect" : "Connect"}</button></header>
        {state.connected ? <fieldset><legend>Permissions</legend>{state.permissions.map((permission) => <label key={permission.id}><input checked={permission.enabled} disabled={busy} onChange={(event) => void onRun(() => connections.permission(tool.id, permission.id, event.target.checked))} type="checkbox" />{permission.name}</label>)}</fieldset> : null}
        <footer><button disabled={busy} onClick={() => void onRun(() => connections.disconnect(tool.id))} type="button">Remove plugin</button></footer>
      </section>
    </details>
  </section>;
}
