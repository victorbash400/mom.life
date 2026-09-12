"use client";

import { useFamily } from "./FamilyProvider";
import { childAvatarStyle } from "./ChildAvatar";
import { ParentAvatar } from "./ParentAvatar";
import type { SimulatorProfile } from "../types/simulator";
import styles from "./SimulatorProfilePicker.module.css";


export function SimulatorProfilePicker({ profiles, selectedId, onSelect }: { profiles: SimulatorProfile[]; selectedId?: string; onSelect: (id: string) => void }) {
  const { family } = useFamily();
  return <nav aria-label="Simulated family profile" className={styles.picker}>{profiles.map((profile) => {
    const child = family.children.find((item) => item.id === profile.id);
    return <button aria-pressed={selectedId === profile.id} key={profile.id} onClick={() => onSelect(profile.id)} type="button">
      {profile.role === "adult" ? <ParentAvatar parent={family.parent} size={28} /> : <i aria-hidden="true" style={child ? childAvatarStyle(child) : undefined} />}
      <span>{profile.name}</span>
    </button>;
  })}</nav>;
}
