"use client";

import { toolById } from "../data/toolDirectory";
import type { useSimulator } from "../hooks/useSimulator";
import { ToolIcon } from "./ToolIcon";
import styles from "./SimulatorConnections.module.css";


const ids = ["apple-health", "whatsapp", "fitbit", "withings", "instacart"];
type Simulator = ReturnType<typeof useSimulator>;

export function SimulatorConnections({ simulator }: { simulator: Simulator }) {
  if (!simulator.state) return null;
  const connections = new Map(simulator.state.connections.map((item) => [item.id, item.connected]));
  return <section className={styles.connections}>{ids.map((id) => {
    const tool = toolById(id);
    if (!tool) return null;
    const connected = connections.get(id) ?? false;
    return <article key={id}><ToolIcon size="small" tool={tool} /><span><strong>{tool.name}</strong><small>{connected ? "Simulator connected" : "Not connected"}</small></span><button className={connected ? styles.disconnect : styles.connect} disabled={simulator.busy} onClick={() => void (connected ? simulator.disconnect(id) : simulator.connect(id))} type="button">{connected ? "Disconnect" : "Connect"}</button></article>;
  })}</section>;
}
