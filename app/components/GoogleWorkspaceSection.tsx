"use client";

import type { ToolState } from "../data/toolDirectory";
import type { useToolConnections } from "../hooks/useToolConnections";
import { GoogleWorkspaceAccount } from "./GoogleWorkspaceAccount";
import { WorkspaceServiceRow, workspaceServices } from "./WorkspaceServiceRow";
import styles from "./GoogleWorkspaceSection.module.css";

type Connections = ReturnType<typeof useToolConnections>;

export function GoogleWorkspaceSection({ busy, connections, onRun, state }: { busy: boolean; connections: Connections; onRun: (action: () => Promise<void>) => Promise<void>; state: ToolState }) {
  const authorized = Boolean(state.account_label);
  const connect = state.connected
    ? () => connections.disconnect(state.id)
    : authorized ? () => connections.validate(state.id) : () => connections.authorize(state.id);

  return <section className={styles.section}>
    <header><span><h2>Workspace</h2><p>Google services available to mom.life.</p></span><button disabled={busy} onClick={() => void onRun(() => connections.disconnect(state.id))} type="button">Remove</button></header>
    <div className={styles.list}>
      <GoogleWorkspaceAccount busy={busy} onConnect={() => void onRun(connect)} state={state} />
      {workspaceServices.map((service, index) => {
        const permission = state.permissions.find((item) => item.id === service.id) || { id: service.id, name: service.name, enabled: true };
        return <WorkspaceServiceRow connected={state.connected} disabled={busy} index={index} key={permission.id} onToggle={() => void onRun(() => connections.permission(state.id, permission.id, !permission.enabled))} permission={permission} />;
      })}
    </div>
  </section>;
}
