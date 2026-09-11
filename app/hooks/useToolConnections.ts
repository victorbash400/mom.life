"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ToolState } from "../data/toolDirectory";


export function useToolConnections() {
  const [states, setStates] = useState<ToolState[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string>();
  const refreshPromise = useRef<Promise<void> | undefined>(undefined);
  const refresh = useCallback(async () => {
    if (refreshPromise.current) return refreshPromise.current;
    const request = (async () => {
      try {
        const response = await fetch("/api/plugins", { cache: "no-store" });
        const payload = await response.json() as { plugins?: ToolState[]; error?: string };
        if (!response.ok || !payload.plugins) throw new Error(payload.error || "Could not load connections.");
        setStates(payload.plugins); setError(undefined);
      } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load connections."); }
      finally { setLoaded(true); }
    })();
    refreshPromise.current = request;
    try { await request; }
    finally { if (refreshPromise.current === request) refreshPromise.current = undefined; }
  }, []);
  useEffect(() => {
    const frame = requestAnimationFrame(() => { void refresh(); });
    const onMessage = (event: MessageEvent) => {
      if (event.origin === window.location.origin && event.data?.type === "mom-life-plugin-connected") void refresh();
    };
    window.addEventListener("message", onMessage);
    window.addEventListener("focus", refresh);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("message", onMessage);
      window.removeEventListener("focus", refresh);
    };
  }, [refresh]);
  async function connect(id: string) {
    const installed = await mutate<ToolState>(`/api/plugins/${id}`, "POST");
    setStates((current) => current.map((state) => state.id === id ? { ...state, ...installed } : state));
  }
  async function authorize(id: string) {
    const authorizationTab = window.open("about:blank", "_blank");
    if (!authorizationTab) throw new Error("Allow new tabs to connect this plugin.");
    try {
      const response = await fetch(`/api/plugins/${id}/authorize`, { method: "POST" });
      const payload = await response.json() as { authorization_url?: string; error?: string };
      if (!response.ok || !payload.authorization_url) throw new Error(payload.error || "Could not start authorization.");
      authorizationTab.location.replace(payload.authorization_url);
      setError(undefined);
    } catch (reason) {
      authorizationTab.close();
      throw reason;
    }
  }
  async function validate(id: string) { try { await mutate(`/api/plugins/${id}/validate`, "POST"); } finally { await refresh(); } }
  async function permission(id: string, permissionId: string, enabled: boolean) { const response = await fetch(`/api/plugins/${id}/permissions`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ permission_id: permissionId, enabled }) }); if (!response.ok) throw new Error("Could not update permission."); await refresh(); }
  async function disconnect(id: string) { await mutate(`/api/plugins/${id}`, "DELETE"); await refresh(); }
  async function simulate(id: string) { await mutate(`/api/simulator/connections/${id}`, "PUT"); await refresh(); }
  async function disconnectSimulation(id: string) { await mutate(`/api/simulator/connections/${id}`, "DELETE"); await refresh(); }
  return { connectedIds: states.filter((state) => state.connected).map((state) => state.id), installedIds: states.filter((state) => state.installed).map((state) => state.id), states, loaded, error, connect, disconnect, disconnectSimulation, refresh, simulate, validate, permission, authorize };
}
async function mutate<T = void>(path: string, method: "POST" | "PUT" | "DELETE") { const response = await fetch(path, { method }); if (!response.ok) { const payload = await response.json().catch(() => ({})) as { error?: string }; throw new Error(payload.error || "Could not update this connection."); } return response.status === 204 ? undefined as T : response.json() as Promise<T>; }
