"use client";

import { SendHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import type { useSimulator } from "../hooks/useSimulator";
import { SimulatorProfilePicker } from "./SimulatorProfilePicker";
import styles from "./SimulatorWhatsApp.module.css";


type Simulator = ReturnType<typeof useSimulator>;

export function SimulatorWhatsApp({ simulator }: { simulator: Simulator }) {
  const state = simulator.state;
  const [selectedId, setSelectedId] = useState(state?.profiles[0]?.id);
  const [text, setText] = useState("");
  const profiles = useMemo(() => new Map(state?.profiles.map((profile) => [profile.id, profile]) ?? []), [state?.profiles]);
  const connected = state?.connections.some((item) => item.id === "whatsapp" && item.connected);
  async function send() {
    if (!selectedId || !text.trim()) return;
    const content = text.trim(); setText("");
    try { await simulator.sendWhatsApp(selectedId, content); }
    catch { setText(content); }
  }
  if (!state) return null;
  return <section className={styles.whatsapp}>
    <SimulatorProfilePicker onSelect={setSelectedId} profiles={state.profiles} selectedId={selectedId} />
    <div aria-live="polite" className={styles.messages}>{state.messages.length ? state.messages.map((message) => <article data-direction={message.direction} key={message.id}><small>{message.direction === "incoming" ? profiles.get(message.profile_id)?.name : "mom.life"}</small><p>{message.body}</p></article>) : <p className={styles.empty}>No simulated messages.</p>}</div>
    <form onSubmit={(event) => { event.preventDefault(); void send(); }}><input aria-label="Simulated WhatsApp message" disabled={!connected || simulator.busy} onChange={(event) => setText(event.target.value)} placeholder={connected ? "Type a message" : "Connect WhatsApp Simulator"} value={text} /><button aria-label="Send simulated message" disabled={!connected || simulator.busy || !text.trim()} type="submit"><SendHorizontal aria-hidden="true" /></button></form>
  </section>;
}
