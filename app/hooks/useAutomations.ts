"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { subscribeFamilyEvents } from "../lib/familyEvents";
import type { AutomationState } from "../types/automations";

export function useAutomations() {
  const [state, setState] = useState<AutomationState>();
  const [error, setError] = useState("");
  const revision = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++revision.current;
    try {
      const response = await fetch("/api/automations", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load automations.");
      if (version === revision.current) { setState(payload); setError(""); }
    } catch (cause) { if (version === revision.current) setError(cause instanceof Error ? cause.message : "Could not load automations."); }
  }, []);
  useEffect(() => {
    void Promise.resolve().then(refresh);
    const requestRevision = revision;
    const unsubscribe = subscribeFamilyEvents({ onEvent: (event) => { if (event.type === "automations_changed" || event.type === "goals_changed") void refresh(); }, onConnection: (connected) => { if (connected) void refresh(); } });
    return () => { requestRevision.current++; unsubscribe(); };
  }, [refresh]);
  async function change(id: string, method: string, body?: object) {
    const response = await fetch(`/api/automations/${id}`, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
    if (!response.ok) { const payload = await response.json(); throw new Error(payload.error || "Could not update automation."); }
    await refresh();
  }
  return { state, error, change };
}
