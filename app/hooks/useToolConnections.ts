"use client";
import { useCallback, useEffect, useState } from "react";
import type { ToolState } from "../data/toolDirectory";


export function useToolConnections() {
  const [states, setStates] = useState<ToolState[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string>();
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/plugins", { cache: "no-store" });
      const payload = await response.json() as { plugins?: ToolState[]; error?: string };
      if (!response.ok || !payload.plugins) throw new Error(payload.error || "Could not load connections.");
      setStates(payload.plugins); setError(undefined);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load connections."); }
    finally { setLoaded(true); }
  }, []);
  useEffect(() => { const frame = requestAnimationFrame(() => { void refresh(); }); return () => cancelAnimationFrame(frame); }, [refresh]);
  async function connect(id: string) { await mutate(`/api/plugins/${id}`, "POST"); await refresh(); }
  async function authorize(id: string) { const response = await fetch(`/api/plugins/${id}/authorize`, { method: "POST" }); const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "Could not start authorization."); window.location.assign(payload.authorization_url); }
  async function validate(id: string) { try { await mutate(`/api/plugins/${id}/validate`, "POST"); } finally { await refresh(); } }
  async function permission(id: string, permissionId: string, enabled: boolean) { const response = await fetch(`/api/plugins/${id}/permissions`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ permission_id: permissionId, enabled }) }); if (!response.ok) throw new Error("Could not update permission."); await refresh(); }
  async function disconnect(id: string) { await mutate(`/api/plugins/${id}`, "DELETE"); await refresh(); }
  async function simulate(id: string) { await mutate(`/api/simulator/connections/${id}`, "PUT"); await refresh(); }
  async function disconnectSimulation(id: string) { await mutate(`/api/simulator/connections/${id}`, "DELETE"); await refresh(); }
  return { connectedIds: states.filter((state) => state.connected).map((state) => state.id), installedIds: states.filter((state) => state.installed).map((state) => state.id), states, loaded, error, connect, disconnect, disconnectSimulation, refresh, simulate, validate, permission, authorize };
}
async function mutate(path: string, method: "POST" | "PUT" | "DELETE") { const response = await fetch(path, { method }); if (!response.ok) { const payload = await response.json().catch(() => ({})) as { error?: string }; throw new Error(payload.error || "Could not update this connection."); } }
