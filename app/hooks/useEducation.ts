"use client";

import { useCallback, useEffect, useState } from "react";
import type { EducationSnapshot } from "../types/education";

export function useEducation() {
  const [snapshots, setSnapshots] = useState<EducationSnapshot[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/education", { cache: "no-store" });
      const payload = await response.json() as { snapshots?: EducationSnapshot[]; error?: string };
      if (!response.ok || !payload.snapshots) throw new Error(payload.error || "Could not load education.");
      setSnapshots(payload.snapshots);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load education.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    const frame = requestAnimationFrame(() => void refresh());
    const events = new EventSource("/api/tasks/events");
    events.onmessage = (message) => {
      const event = JSON.parse(message.data) as { type?: string };
      if (event.type === "education_changed") void refresh();
    };
    events.onerror = () => setError("Live education updates are disconnected. Reconnecting…");
    return () => { cancelAnimationFrame(frame); events.close(); };
  }, [refresh]);

  return { error, loaded, snapshots };
}
