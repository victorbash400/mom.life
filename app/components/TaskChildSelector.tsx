"use client";

import type { ChildProfile } from "../types/dashboard";
import { childAvatarStyle } from "./ChildAvatar";
import { Check, ChevronDown, UsersRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useFamily } from "./FamilyProvider";
import styles from "./TaskChildSelector.module.css";

export function TaskChildSelector({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { family: { children } } = useFamily();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const selected = children.find((child) => child.id === value);

  useEffect(() => {
    function close(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  function select(next: string) {
    onChange(next);
    setOpen(false);
  }

  return <div className={styles.selector} ref={root}><button aria-expanded={open} aria-haspopup="listbox" onClick={() => setOpen((current) => !current)} type="button"><Avatar child={selected} /><span><small>For</small><strong>{selected?.name ?? "All Children"}</strong></span><ChevronDown className={styles.chevron} /></button>{open ? <div aria-label="Choose a child" className={styles.menu} role="listbox"><Option active={value === "all"} label="All Children" onSelect={() => select("all")} /><div className={styles.rule} />{children.map((child) => <Option active={value === child.id} key={child.id} label={child.name} onSelect={() => select(child.id)} child={child} />)}</div> : null}</div>;
}

function Avatar({ child }: { child?: ChildProfile }) {
  return child ? <i className={styles.avatar} style={childAvatarStyle(child!)} /> : <i className={styles.family}><UsersRound /></i>;
}

function Option({ active, label, child, onSelect }: { active: boolean; label: string; child?: ChildProfile; onSelect: () => void }) {
  return <button aria-selected={active} onClick={onSelect} role="option" type="button"><Avatar child={child} /><span>{label}</span>{active ? <Check /> : null}</button>;
}
