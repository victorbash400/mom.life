"use client";

import { useState } from "react";
import type { useSimulator } from "../hooks/useSimulator";
import { SimulatorHealthForm } from "./SimulatorHealthForm";
import { SimulatorProfilePicker } from "./SimulatorProfilePicker";
import styles from "./SimulatorHealth.module.css";


type Simulator = ReturnType<typeof useSimulator>;
export function SimulatorHealth({ simulator }: { simulator: Simulator }) {
  const state = simulator.state;
  const children = state?.profiles.filter((profile) => profile.role === "child") ?? [];
  const [selectedId, setSelectedId] = useState(children[0]?.id);
  const connected = state?.connections.some((item) => ["apple-health", "fitbit", "withings"].includes(item.id) && item.connected);
  if (!state) return null;
  return <section className={styles.health}>
    <header><SimulatorProfilePicker onSelect={setSelectedId} profiles={children} selectedId={selectedId} />{selectedId ? <SimulatorHealthForm childId={selectedId} connected={Boolean(connected)} initialDate={state.health.date} initialValues={state.health.profiles[selectedId]} key={selectedId} simulator={simulator} /> : null}</header>
  </section>;
}
