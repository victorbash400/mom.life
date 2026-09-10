"use client";

import Image from "next/image";
import { useFamily } from "./FamilyProvider";
import { childAvatarStyle } from "./ChildAvatar";
import type { SimulatorProfile } from "../types/simulator";
import styles from "./SimulatorProfilePicker.module.css";


export function SimulatorProfilePicker({ profiles, selectedId, onSelect }: { profiles: SimulatorProfile[]; selectedId?: string; onSelect: (id: string) => void }) {
  const { family } = useFamily();
  return <nav aria-label="Simulated family profile" className={styles.picker}>{profiles.map((profile) => {
    const child = family.children.find((item) => item.id === profile.id);
    return <button aria-pressed={selectedId === profile.id} key={profile.id} onClick={() => onSelect(profile.id)} type="button">
      {profile.role === "adult" ? <Image alt="" height={34} src="/sarah-profile.png" width={34} /> : <i aria-hidden="true" style={child ? childAvatarStyle(child) : undefined} />}
      <span>{profile.name}</span>
    </button>;
  })}</nav>;
}
