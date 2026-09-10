"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState, type CSSProperties } from "react";

import { toolDirectory } from "../data/toolDirectory";
import { ConnectedToolIcon } from "./ConnectedToolIcon";
import styles from "./UtilityNav.module.css";

const collapsedLimit = 6;

export function UtilityNav({ connectedIds }: { connectedIds: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const connected = toolDirectory.filter((tool) => connectedIds.includes(tool.id));
  if (!connected.length) return null;

  const primary = connected.slice(0, collapsedLimit);
  const overflow = connected.slice(collapsedLimit);
  const overflowWidth = overflow.length * 36 + Math.max(0, overflow.length - 1) * 17;

  return <nav className={styles.nav} aria-label="Connected tools" data-expanded={expanded}>
    {primary.map((tool) => <button aria-label={tool.name} className={styles.tool} data-tooltip={tool.name} key={tool.id} type="button"><ConnectedToolIcon tool={tool} /></button>)}
    {overflow.length ? <span aria-hidden={!expanded} className={styles.overflow} style={{ "--overflow-width": `${overflowWidth}px` } as CSSProperties}>
      {overflow.map((tool) => <button aria-label={tool.name} className={styles.tool} data-tooltip={tool.name} key={tool.id} tabIndex={expanded ? 0 : -1} type="button"><ConnectedToolIcon tool={tool} /></button>)}
    </span> : null}
    {overflow.length ? <button aria-expanded={expanded} aria-label={expanded ? "Show fewer connections" : `Show ${overflow.length} more connections`} className={styles.toggle} data-tooltip={expanded ? "Show fewer" : `${overflow.length} more`} onClick={() => setExpanded((current) => !current)} type="button">
      {expanded ? <ChevronLeft aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
    </button> : null}
  </nav>;
}
