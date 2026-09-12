"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { subscribeFamilyEvents } from "../lib/familyEvents";

import type { SecuritySettings, SecuritySnapshot } from "../types/security";

export function useSecurity(enabled = true) {
  const [snapshot, setSnapshot] = useState<SecuritySnapshot>();
  const [error, setError] = useState<string>();
  const [alertCount, setAlertCount] = useState(0);
  const connectedOnce = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/security", { cache: "no-store" });
      const payload = await response.json() as SecuritySnapshot | { error?: string };
      if (!response.ok || !("reviews" in payload)) throw new Error("error" in payload && payload.error || "Could not load safety alerts.");
      setSnapshot(payload);
      setAlertCount(payload.reviews.filter((review) => review.status === "completed" && review.action === "alert" && !review.dismissed).length);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load safety alerts.");
    }
  }, []);

  const refreshCount = useCallback(async () => {
    try {
      const response = await fetch("/api/security/summary", { cache: "no-store" });
      const payload = await response.json() as { alert_count?: number; error?: string };
      if (!response.ok || typeof payload.alert_count !== "number") throw new Error(payload.error || "Could not load safety alerts.");
      setAlertCount(payload.alert_count);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load safety alerts.");
    }
  }, []);

  const saveSettings = useCallback(async (settings: Omit<SecuritySettings, "family_id" | "updated_at">) => {
    const response = await fetch("/api/security/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings) });
    const payload = await response.json() as SecuritySettings | { error?: string };
    if (!response.ok || !("alert_level" in payload)) throw new Error("error" in payload && payload.error || "Could not save safety settings.");
    setSnapshot((current) => current ? { ...current, settings: payload } : current);
  }, []);

  const act = useCallback(async (reviewId: string, action: "retry" | "dismiss") => {
    const response = await fetch(`/api/security/reviews/${encodeURIComponent(reviewId)}/${action}`, { method: "POST" });
    const payload = await response.json() as { error?: string };
    if (!response.ok) throw new Error(payload.error || `Could not ${action} the safety review.`);
    await refresh();
  }, [refresh]);

  const retry = useCallback((reviewId: string) => act(reviewId, "retry"), [act]);
  const dismiss = useCallback((reviewId: string) => act(reviewId, "dismiss"), [act]);

  useEffect(() => {
    connectedOnce.current = false;
    const load = enabled ? refresh : refreshCount;
    const frame = requestAnimationFrame(() => void load());
    const unsubscribe = subscribeFamilyEvents({
      onEvent: (event) => { if (event.type === "security_changed") void load(); },
      onConnection: (connected) => {
        if (!connected) return setError("Live safety updates are disconnected. Reconnecting…");
        if (connectedOnce.current) void load();
        connectedOnce.current = true;
      },
    });
    return () => { cancelAnimationFrame(frame); unsubscribe(); };
  }, [enabled, refresh, refreshCount]);

  return { alertCount, dismiss, error, loaded: Boolean(snapshot), refresh, reviews: snapshot?.reviews ?? [], retry, saveSettings, settings: snapshot?.settings };
}

export type SecurityState = ReturnType<typeof useSecurity>;
