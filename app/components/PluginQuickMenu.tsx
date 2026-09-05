"use client";
import { ArrowRight, Plug, X } from "lucide-react";
import { useState } from "react";
import { toolDirectory } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./PluginQuickMenu.module.css";
export function PluginQuickMenu({ connectedIds, onClose, onDisconnect, onStore }: { connectedIds: string[]; onClose: () => void; onDisconnect: (id: string) => Promise<void>; onStore: () => void }) {
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState<string>();
  async function disconnect(id: string) { setBusy(id); setError(undefined); try { await onDisconnect(id); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not disconnect this tool."); } finally { setBusy(undefined); } }
  const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id));
  return <aside aria-label="Connections" className={styles.menu}><header><strong>Connections</strong><button aria-label="Close connections" onClick={onClose} type="button"><X /></button></header>{connected.length ? <section className={styles.tools}>{connected.map((tool) => <article key={tool.id}><ToolIcon size="small" tool={tool} /><span><strong>{tool.name}</strong><small>Connected</small></span><button aria-label={`Disconnect ${tool.name}`} disabled={Boolean(busy)} onClick={() => void disconnect(tool.id)} type="button">Disconnect</button></article>)}</section> : <section className={styles.empty}><Plug /><span><strong>No connections</strong><small>Connect a tool when you need one.</small></span></section>}{error ? <p className={styles.error} role="alert">{error}</p> : null}<footer><button className={styles.store} onClick={onStore} type="button">Browse tools<ArrowRight /></button></footer></aside>;
}
