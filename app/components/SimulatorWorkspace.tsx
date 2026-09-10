"use client";

import { useState } from "react";
import type { useSimulator } from "../hooks/useSimulator";
import { SimulatorConnections } from "./SimulatorConnections";
import { SimulatorDevice, type SimulatorView } from "./SimulatorDevice";
import { SimulatorHealth } from "./SimulatorHealth";
import { SimulatorWhatsApp } from "./SimulatorWhatsApp";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./SimulatorWorkspace.module.css";


type Simulator = ReturnType<typeof useSimulator>;

export function SimulatorWorkspace({ onClose, simulator }: { onClose: () => void; simulator: Simulator }) {
  const [view, setView] = useState<SimulatorView>("whatsapp");
  return <section className={styles.workspace}>
    <WorkspaceHeader onClose={onClose} title="Simulator" />
    {simulator.error ? <p className={styles.error} role="alert">{simulator.error}</p> : null}
    <SimulatorDevice onViewChange={setView} view={view}>{view === "whatsapp" ? <SimulatorWhatsApp simulator={simulator} /> : view === "health" ? <SimulatorHealth simulator={simulator} /> : <SimulatorConnections simulator={simulator} />}</SimulatorDevice>
  </section>;
}
