"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import { preload } from "react-dom";
import { childAvatarUrl } from "./ChildAvatar";
import type { ChildProfile, PersonProfile } from "../types/dashboard";
export type Family = { id: string; parent: PersonProfile; children: ChildProfile[] };
const Context = createContext<{ family: Family; refresh: () => Promise<void> } | null>(null);
export function FamilyProvider({ initial, children }: { initial: Family; children: ReactNode }) {
  const [family, setFamily] = useState(initial);
  for (const child of family.children) preload(childAvatarUrl(child), { as: "image" });
  async function refresh() {
    const response = await fetch("/api/family", { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load family profiles.");
    setFamily(await response.json());
  }
  return <Context.Provider value={{ family, refresh }}>{children}</Context.Provider>;
}
export function useFamily() {
  const value = useContext(Context);
  if (!value) throw new Error("Family context is missing.");
  return value;
}
