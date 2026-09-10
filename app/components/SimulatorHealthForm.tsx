"use client";

import { useState } from "react";
import type { useSimulator } from "../hooks/useSimulator";
import type { SimulatorHealthValues } from "../types/simulator";
import styles from "./SimulatorHealth.module.css";


type Simulator = ReturnType<typeof useSimulator>;
type Values = { steps: number; sleep_hours: number; heart_rate: number; active_energy: number; distance: number };
const defaults: Values = { steps: 6200, sleep_hours: 8.4, heart_rate: 78, active_energy: 320, distance: 4100 };

export function SimulatorHealthForm({ childId, connected, initialDate, initialValues, simulator }: { childId: string; connected: boolean; initialDate: string; initialValues?: SimulatorHealthValues; simulator: Simulator }) {
  const [date, setDate] = useState(initialDate);
  const [values, setValues] = useState<Values>({
    steps: initialValues?.step_count ?? defaults.steps,
    sleep_hours: initialValues?.sleep_analysis ?? defaults.sleep_hours,
    heart_rate: initialValues?.heart_rate ?? defaults.heart_rate,
    active_energy: initialValues?.active_energy ?? defaults.active_energy,
    distance: initialValues?.walking_running_distance ?? defaults.distance,
  });
  function field(key: keyof Values, value: string) { setValues((current) => ({ ...current, [key]: Number(value) })); }
  return <>
    <input aria-label="Health sample date" className={styles.date} onChange={(event) => setDate(event.target.value)} type="date" value={date} />
    <div className={styles.fields}>
      <label><span>Steps</span><input min="0" onChange={(event) => field("steps", event.target.value)} type="number" value={values.steps} /></label>
      <label><span>Sleep</span><span><input max="24" min="0" onChange={(event) => field("sleep_hours", event.target.value)} step="0.1" type="number" value={values.sleep_hours} /><small>hours</small></span></label>
      <label><span>Heart rate</span><span><input max="240" min="20" onChange={(event) => field("heart_rate", event.target.value)} type="number" value={values.heart_rate} /><small>bpm</small></span></label>
      <label><span>Active energy</span><span><input min="0" onChange={(event) => field("active_energy", event.target.value)} type="number" value={values.active_energy} /><small>kcal</small></span></label>
      <label><span>Distance</span><span><input min="0" onChange={(event) => field("distance", event.target.value)} type="number" value={values.distance} /><small>metres</small></span></label>
    </div>
    <button className={styles.save} disabled={!connected || simulator.busy} onClick={() => void simulator.saveHealth({ child_id: childId, date, ...values })} type="button">{connected ? "Sync health data" : "Connect a health simulator"}</button>
  </>;
}
