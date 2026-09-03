"use client";
import { useEffect, useState } from "react";

const storageKey = "mom-life-tool-connections-v1";
export function useToolConnections() {
  const [connectedIds, setConnectedIds] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { const frame = requestAnimationFrame(() => { const saved = localStorage.getItem(storageKey); setConnectedIds(saved ? JSON.parse(saved) as string[] : []); setLoaded(true); }); return () => cancelAnimationFrame(frame); }, []);
  function set(ids: string[]) { setConnectedIds(ids); localStorage.setItem(storageKey, JSON.stringify(ids)); }
  return { connectedIds, loaded, connect: (id: string) => set([...new Set([...connectedIds, id])]), disconnect: (id: string) => set(connectedIds.filter((current) => current !== id)) };
}
