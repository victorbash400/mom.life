"use client";

import { useCallback, useEffect, useState } from "react";

import type { SecuritySettings, SecuritySnapshot } from "../types/security";

export function useSecurity() {
  const [snapshot, setSnapshot] = useState<SecuritySnapshot>();
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/security", { cache: "no-store" });
      const payload = await response.json() as SecuritySnapshot | { error?: string };
      if (!response.ok || !("reviews" in payload)) throw new Error("error" in payload && payload.error || "Could not load security alerts.");
      setSnapshot(payload);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load security alerts.");
    }
  }, []);

  const saveSettings = useCallback(async (settings: Pick<SecuritySettings, "enabled" | "alert_level" | "instructions">) => {
    const response = await fetch("/api/security/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings) });
    const payload = await response.json() as SecuritySettings | { error?: string };
    if (!response.ok || !("alert_level" in payload)) throw new Error("error" in payload && payload.error || "Could not save security settings.");
    setSnapshot((current) => current ? { ...current, settings: payload } : current);
  }, []);

  const act = useCallback(async (reviewId: string, action: "retry" | "dismiss") => {
    const response = await fetch(`/api/security/reviews/${encodeURIComponent(reviewId)}/${action}`, { method: "POST" });
    const payload = await response.json() as { error?: string };
    if (!response.ok) throw new Error(payload.error || `Could not ${action} the security review.`);
    await refresh();
  }, [refresh]);

  const retry = useCallback((reviewId: string) => act(reviewId, "retry"), [act]);
  const dismiss = useCallback((reviewId: string) => act(reviewId, "dismiss"), [act]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => void refresh());
    const events = new EventSource("/api/tasks/events");
    events.onmessage = (message) => {
      const event = JSON.parse(message.data) as { type?: string };
      if (event.type === "security_changed") void refresh();
    };
    events.onerror = () => setError("Live security updates are disconnected. Reconnecting…");
    return () => { cancelAnimationFrame(frame); events.close(); };
  }, [refresh]);

  return { dismiss, error, loaded: Boolean(snapshot), refresh, reviews: snapshot?.reviews ?? [], retry, saveSettings, settings: snapshot?.settings };
}

export type SecurityState = ReturnType<typeof useSecurity>;
