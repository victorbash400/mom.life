"use client";

import { Check, ChevronDown, type LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import styles from "./TaskPicker.module.css";

type Option = { label: string; value: string };

export function TaskPicker({ icon: Icon, label, onChange, options, value }: { icon: LucideIcon; label: string; onChange: (value: string) => void; options: Option[]; value: string }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    function close(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  return <div className={styles.picker} ref={root}>
    <button aria-expanded={open} aria-haspopup="listbox" aria-label={label} onClick={() => setOpen((current) => !current)} type="button"><Icon aria-hidden="true" /><span>{selected.label}</span><ChevronDown aria-hidden="true" className={styles.chevron} /></button>
    {open ? <div aria-label={label} className={styles.menu} role="listbox">{options.map((option) => <button aria-selected={option.value === value} key={option.value} onClick={() => { onChange(option.value); setOpen(false); }} role="option" type="button"><span>{option.label}</span>{option.value === value ? <Check aria-hidden="true" /> : null}</button>)}</div> : null}
  </div>;
}
