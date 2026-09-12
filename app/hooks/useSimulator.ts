"use client";

import { useCallback, useEffect, useState } from "react";
import type { SimulatorMessage, SimulatorState } from "../types/simulator";


export function useSimulator(afterMutation?: () => Promise<void>, enabled = true) {
  const [state, setState] = useState<SimulatorState>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    const response = await fetch("/api/simulator", { cache: "no-store" });
    if (!hasSession(response)) return;
    const payload = await response.json() as SimulatorState & { error?: string };
    if (!response.ok) throw new Error(payload.error || "Could not load the simulator.");
    setState(payload); setError(undefined);
  }, []);
  useEffect(() => {
    if (!enabled) return;
    const frame = requestAnimationFrame(() => void refresh().catch((reason) => setError(message(reason))));
    return () => cancelAnimationFrame(frame);
  }, [enabled, refresh]);
  async function run(path: string, method: "PUT" | "DELETE", refreshConnections = false, body?: object) {
    setBusy(true); setError(undefined);
    try {
      const response = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
      if (!hasSession(response)) return;
      const payload = response.status === 204 ? undefined : await response.json();
      if (!response.ok) throw new Error(payload?.error || "The simulator could not complete that action.");
      await Promise.all([refresh(), refreshConnections ? afterMutation?.() : undefined]);
      return payload;
    } catch (reason) { setError(message(reason)); throw reason; }
    finally { setBusy(false); }
  }
  async function sendWhatsApp(profileId: string, text: string) {
    const optimistic: SimulatorMessage = { id: crypto.randomUUID(), profile_id: profileId, direction: "incoming", body: text, created_at: new Date().toISOString() };
    setError(undefined);
    setState((current) => current ? { ...current, messages: [...current.messages, optimistic] } : current);
    try {
      const response = await fetch("/api/simulator/whatsapp/messages", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile_id: profileId, text }) });
      if (!hasSession(response)) return;
      const payload = await response.json() as { message?: SimulatorMessage; error?: string };
      if (!response.ok || !payload.message) throw new Error(payload.error || "The message could not be sent.");
      setState((current) => current ? { ...current, messages: current.messages.map((message) => message.id === optimistic.id ? payload.message! : message) } : current);
    } catch (reason) {
      setState((current) => current ? { ...current, messages: current.messages.filter((message) => message.id !== optimistic.id) } : current);
      setError(message(reason));
      throw reason;
    }
  }
  return {
    state, error, busy, refresh,
    connect: (id: string) => run(`/api/simulator/connections/${encodeURIComponent(id)}`, "PUT", true),
    disconnect: (id: string) => run(`/api/simulator/connections/${encodeURIComponent(id)}`, "DELETE", true),
    sendWhatsApp,
    saveHealth: (values: object) => run("/api/simulator/health", "PUT", false, values),
  };
}

function hasSession(response: Response) {
  if (response.status !== 401) return true;
  window.location.replace("/sign-in");
  return false;
}

function message(reason: unknown) { return reason instanceof Error ? reason.message : "The simulator could not complete that action."; }
