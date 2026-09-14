"use client";

import { useState } from "react";
import type { useSimulator } from "../hooks/useSimulator";
import { SimulatorProfilePicker } from "./SimulatorProfilePicker";
import { SimulatorMessageList } from "./SimulatorMessageList";
import { SimulatorMessageComposer } from "./SimulatorMessageComposer";
import styles from "./SimulatorWhatsApp.module.css";

type Simulator = ReturnType<typeof useSimulator>;

export function SimulatorWhatsApp({ simulator }: { simulator: Simulator }) {
  const state = simulator.state;
  const [selectedId, setSelectedId] = useState(state?.profiles[0]?.id);
  if (!state) return null;
  const profile = state.profiles.find((item) => item.id === selectedId);
  if (!profile) return null;
  const connected = state.connections.some((item) => item.id === "whatsapp" && item.connected);
  const messages = state.messages.filter((message) => message.profile_id === profile.id);
  return <section aria-label={`${profile.name}'s WhatsApp inbox`} className={styles.whatsapp}>
    <SimulatorProfilePicker onSelect={setSelectedId} profiles={state.profiles} selectedId={profile.id} />
    <small className={styles.number}>{profile.phone_number}</small>
    <SimulatorMessageList messages={messages} profileName={profile.name} />
    <SimulatorMessageComposer connected={Boolean(connected)} key={profile.id} profile={profile} send={simulator.sendWhatsApp} />
  </section>;
}
