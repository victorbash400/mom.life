"use client";

import { useCallback, useEffect, useState } from "react";
import { subscribeFamilyEvents } from "../lib/familyEvents";

import type { IncomingItem } from "../types/intake";

export function useIncomingItems() {
  const [items, setItems] = useState<IncomingItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/incoming", { cache: "no-store" });
      const payload = await response.json() as IncomingItem[] | { error?: string };
      if (!response.ok || !Array.isArray(payload)) throw new Error(!Array.isArray(payload) && payload.error || "Could not load incoming items.");
      setItems(payload);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load incoming items.");
    } finally {
      setLoaded(true);
    }
  }, []);

  const retry = useCallback(async (id: string) => {
    const response = await fetch(`/api/incoming/${encodeURIComponent(id)}/retry`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const payload = await response.json() as { error?: string };
    if (!response.ok) throw new Error(payload.error || "Could not retry the Intake Agent.");
    await refresh();
  }, [refresh]);

  const remove = useCallback(async (id: string) => {
    const response = await fetch(`/api/incoming/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({})) as { error?: string };
      throw new Error(payload.error || "Could not delete the item.");
    }
    await refresh();
  }, [refresh]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => void refresh());
    const unsubscribe = subscribeFamilyEvents({
      onEvent: (event) => { if (event.type === "intake_changed") void refresh(); },
      onConnection: (connected) => { connected ? void refresh() : setError("Live intake updates are disconnected. Reconnecting…"); },
    });
    return () => { cancelAnimationFrame(frame); unsubscribe(); };
  }, [refresh]);

  return { error, items, loaded, remove, retry };
}
