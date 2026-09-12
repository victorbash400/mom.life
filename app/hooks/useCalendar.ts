"use client";

import { useCallback, useEffect, useState } from "react";
import type { CalendarPreferences, CalendarState } from "../types/calendar";

const initial: CalendarState = { connected: false, writable: false, events: [], preferences: { enabled: true, reminder_method: "popup", reminder_minutes: 30 } };

export function useCalendar() {
  const [state, setState] = useState(initial);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/calendar", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load Calendar.");
      setState(payload); setError(undefined);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load Calendar."); }
    finally { setLoaded(true); }
  }, []);
  useEffect(() => { const frame = requestAnimationFrame(() => void refresh()); return () => cancelAnimationFrame(frame); }, [refresh]);
  async function savePreferences(preferences: CalendarPreferences) {
    setBusy(true);
    try {
      const response = await fetch("/api/calendar", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(preferences) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not save reminders.");
      setState((current) => ({ ...current, preferences: payload })); setError(undefined);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save reminders."); }
    finally { setBusy(false); }
  }
  async function request(text: string) {
    setBusy(true);
    try {
      const response = await fetch("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ child_id: "all", text: "Calendar: " + text }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not start this Calendar request.");
      setError(undefined); return payload.id as string;
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not start this Calendar request."); throw cause; }
    finally { setBusy(false); }
  }
  return { ...state, busy, error, loaded, refresh, request, savePreferences };
}
