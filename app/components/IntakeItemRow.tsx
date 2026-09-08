"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import type { IncomingItem } from "../types/intake";
import styles from "./IntakeItemRow.module.css";

export function IntakeItemRow({ item, selected, onSelect, onDelete }: { item: IncomingItem; selected: boolean; onSelect: () => void; onDelete: (id: string) => Promise<void> }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string>();

  async function remove() {
    if (deleting) return;
    setDeleting(true);
    setError(undefined);
    try {
      await onDelete(item.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete the item.");
      setDeleting(false);
    }
  }

  return <div className={styles.item} data-deleting={deleting}>
    <button aria-current={selected ? "true" : undefined} className={styles.row} onClick={onSelect} type="button"><span><strong>{item.sender || item.source}</strong><time dateTime={item.created_at}>{formatTime(item.created_at)}</time></span><b>{item.subject || item.source}</b><p>{singleLine(item.content)}</p><small data-attention={item.attention_required}>{item.attention_required ? "Needs attention" : statusLabel(item)}</small></button>
    <button aria-label={`Delete ${item.subject || item.source}`} className={styles.delete} disabled={deleting} onClick={() => void remove()} title="Delete item" type="button"><Trash2 aria-hidden="true" /></button>
    {error ? <small className={styles.error} role="alert">{error}</small> : null}
  </div>;
}

function singleLine(value: string) { return value.replace(/\s+/g, " ").trim(); }
function statusLabel(item: IncomingItem) {
  if (item.status === "processing" || item.status === "queued") return item.status === "queued" ? "Queued for Intake Agent" : "Intake Agent working";
  if (item.action === "create_goal") return "Started new work";
  if (item.action === "resume_goal") return "Continued active work";
  return "Recorded";
}
function formatTime(value: string) {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" }).format(date);
}
