"use client";

import { useCallback, useEffect, useState } from "react";
import type { SimulatorState } from "../types/simulator";


export function useSimulator(afterMutation?: () => Promise<void>) {
  const [state, setState] = useState<SimulatorState>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    const response = await fetch("/api/simulator", { cache: "no-store" });
    const payload = await response.json() as SimulatorState & { error?: string };
    if (!response.ok) throw new Error(payload.error || "Could not load the simulator.");
    setState(payload); setError(undefined);
  }, []);
  useEffect(() => { const frame = requestAnimationFrame(() => void refresh().catch((reason) => setError(message(reason)))); return () => cancelAnimationFrame(frame); }, [refresh]);
  async function run(path: string, method: "POST" | "PUT" | "DELETE", body?: object) {
    setBusy(true); setError(undefined);
    try {
      const response = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
      const payload = response.status === 204 ? undefined : await response.json();
      if (!response.ok) throw new Error(payload?.error || "The simulator could not complete that action.");
      await Promise.all([refresh(), afterMutation?.()]);
      return payload;
    } catch (reason) { setError(message(reason)); throw reason; }
    finally { setBusy(false); }
  }
  return {
    state, error, busy, refresh,
    connect: (id: string) => run(`/api/simulator/connections/${encodeURIComponent(id)}`, "PUT"),
    disconnect: (id: string) => run(`/api/simulator/connections/${encodeURIComponent(id)}`, "DELETE"),
    sendWhatsApp: (profileId: string, text: string) => run("/api/simulator/whatsapp/messages", "POST", { profile_id: profileId, text }),
    saveHealth: (values: object) => run("/api/simulator/health", "PUT", values),
  };
}

function message(reason: unknown) { return reason instanceof Error ? reason.message : "The simulator could not complete that action."; }
