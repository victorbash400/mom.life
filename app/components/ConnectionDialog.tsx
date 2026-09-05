"use client";
import { useEffect, useRef, useState } from "react";
import type { ToolDefinition } from "../data/toolDirectory";
import type { useToolConnections } from "../hooks/useToolConnections";
import { ConnectionSetup } from "./ConnectionSetup";
import { ToolIcon } from "./ToolIcon";
import styles from "./ConnectionDialog.module.css";
export function ConnectionDialog({ tool, onCancel, connections }: { tool?: ToolDefinition; onCancel: () => void; connections: ReturnType<typeof useToolConnections> }) {
  const ref = useRef<HTMLDialogElement>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  useEffect(() => { if (tool && !ref.current?.open) ref.current?.showModal(); else if (!tool && ref.current?.open) ref.current.close(); }, [tool]);
  const state = connections.states.find((item) => item.id === tool?.id);
  async function act(action: () => Promise<void>) { setBusy(true); setError(undefined); try { await action(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update connection."); } finally { setBusy(false); } }
  return <dialog className={styles.dialog} onCancel={onCancel} ref={ref}>{tool ? <section><header><ToolIcon tool={tool} /><span><h2>{tool.name}</h2><p>{state?.connected ? "Connected" : state?.installed ? "Setup required" : tool.description}</p></span></header><h3>Permissions</h3><ul>{(state?.permissions || tool.permissions.map((name, index) => ({ id: `${tool.id}.${index}`, name, enabled: true }))).map((permission) => <li key={permission.id}><label><input type="checkbox" checked={permission.enabled} disabled={!state?.installed || busy} onChange={(event) => void act(() => connections.permission(tool.id, permission.id, event.target.checked))} /> {permission.name}</label></li>)}</ul>{!state?.connected ? <p className={styles.setup}>{state?.setup_message || tool.setup}</p> : null}{state?.installed && !state.connected && state.setup_fields ? <ConnectionSetup fields={state.setup_fields} /> : null}{error ? <p className={styles.setup} role="alert">{error}</p> : null}<footer><button onClick={onCancel} type="button">Close</button>{state?.installed ? <><button disabled={busy} onClick={() => void act(() => connections.disconnect(tool.id))} type="button">Remove</button>{state.oauth_supported ? <button disabled={busy} onClick={() => void act(() => connections.authorize(tool.id))} type="button">Authorize</button> : null}<button disabled={busy || !state.connection_supported} onClick={() => void act(() => connections.validate(tool.id))} type="button">Check connection</button></> : <button disabled={busy} onClick={() => void act(() => connections.connect(tool.id))} type="button">Install</button>}</footer></section> : null}</dialog>;
}
