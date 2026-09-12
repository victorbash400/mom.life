"use client";

import { useEffect, useState } from "react";
import type { ProfileSource } from "../types/profileSources";

export function useProfileSources() {
  const [sources, setSources] = useState<ProfileSource[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void fetch("/api/family/plugin-access", { cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json() as { sources?: ProfileSource[]; error?: string };
        if (!response.ok || !payload.sources) throw new Error(payload.error || "Could not load data sources.");
        if (active) setSources(payload.sources);
      })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load data sources."); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  async function toggle(profileId: string, pluginId: string, enabled: boolean) {
    const key = `${profileId}:${pluginId}`;
    const previous = sources;
    setBusy(key);
    setError("");
    setSources((current) => current.map((source) => source.id === pluginId ? { ...source, profiles: { ...source.profiles, [profileId]: enabled } } : source));
    try {
      const response = await fetch(`/api/family/plugin-access/${encodeURIComponent(pluginId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId, enabled }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Could not update this data source.");
      }
    } catch (cause) {
      setSources(previous);
      setError(cause instanceof Error ? cause.message : "Could not update this data source.");
    } finally {
      setBusy("");
    }
  }

  return { busy, error, loaded, sources, toggle };
}
