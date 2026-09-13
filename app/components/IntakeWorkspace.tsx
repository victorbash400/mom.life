"use client";

import { useState } from "react";

import { useIncomingItems } from "../hooks/useIncomingItems";
import { IntakeAttentionButton } from "./IntakeAttentionButton";
import { IntakeInbox } from "./IntakeInbox";
import { LoadingIndicator } from "./LoadingIndicator";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./IntakeWorkspace.module.css";

export function IntakeWorkspace({ onClose, initialSelectedId }: { onClose: () => void; initialSelectedId?: string }) {
  const inbox = useIncomingItems();
  const [selectedId, setSelectedId] = useState<string | undefined>(initialSelectedId);
  const attention = inbox.items.filter((item) => item.attention_required);

  return <div className={styles.workspace}><WorkspaceHeader title="Incoming" onClose={onClose} />{inbox.error ? <p className={styles.error} role="alert">{inbox.error}</p> : null}{inbox.loaded ? <section className={styles.panel}><header><strong>Family inbox</strong><span><small>{inbox.items.length} {inbox.items.length === 1 ? "item" : "items"}</small><IntakeAttentionButton count={attention.length} onClick={() => attention[0] && setSelectedId(attention[0].id)} /></span></header><IntakeInbox items={inbox.items} onDelete={inbox.remove} onRetry={inbox.retry} onSelect={setSelectedId} selectedId={selectedId} /></section> : !inbox.error ? <LoadingIndicator className={styles.loading} /> : null}</div>;
}
