"use client";

import { Check, CircleAlert, LoaderCircle, X } from "lucide-react";
import { useEffect, useRef } from "react";

import type { IncomingItem } from "../types/intake";
import { IntakeRetryButton } from "./IntakeRetryButton";
import styles from "./IntakeAgentActivity.module.css";

export function IntakeAgentActivity({ item, onRetry }: { item: IncomingItem; onRetry: (id: string) => Promise<void> }) {
  const running = item.status === "processing" || item.status === "queued";
  const activityRef = useRef<HTMLElement>(null);
  useEffect(() => {
    activityRef.current?.scrollTo({ behavior: "smooth", top: activityRef.current.scrollHeight });
  }, [item.activities.length, item.status]);

  return <aside aria-label="Intake Agent activity" className={styles.activity} ref={activityRef}>
    <header><strong>Intake Agent</strong><span className={styles.controls}><Status status={item.status} /><IntakeRetryButton disabled={running} itemId={item.id} onRetry={onRetry} /></span></header>
    {item.failure ? <p className={styles.failure}><CircleAlert aria-hidden="true" />{item.failure}</p> : null}
    <ol>{item.activities.map((activity, index) => {
      const current = running && index === item.activities.length - 1;
      const failed = item.status === "failed" && index === item.activities.length - 1;
      return <li data-state={failed ? "failed" : current ? "running" : "completed"} key={activity.id}><span className={styles.marker}>{failed ? <X aria-hidden="true" /> : current ? <LoaderCircle aria-hidden="true" /> : <Check aria-hidden="true" />}</span><span className={styles.step}>{activity.summary}</span></li>;
    })}</ol>
  </aside>;
}

function Status({ status }: { status: IncomingItem["status"] }) {
  if (status === "processing" || status === "queued") return <small className={styles.running}><LoaderCircle aria-hidden="true" />{status === "queued" ? "Queued" : "Working"}</small>;
  return <small>{status === "failed" ? "Needs attention" : "Done"}</small>;
}
