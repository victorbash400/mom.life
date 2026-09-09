"use client";

import { CircleUserRound } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import type { ToolState } from "../data/toolDirectory";
import styles from "./GoogleWorkspaceAccount.module.css";

export function GoogleWorkspaceAccount({ busy, onConnect, state }: { busy: boolean; onConnect: () => void; state: ToolState }) {
  const [pictureFailed, setPictureFailed] = useState(false);
  const authorized = Boolean(state.account_label);
  const picture = authorized && state.account_picture && !pictureFailed;
  return <section aria-label="Google account" className={styles.account}>
    <span className={styles.avatar}>{picture ? <Image alt="" height={78} onError={() => setPictureFailed(true)} src={state.account_picture!} unoptimized width={78} /> : <CircleUserRound aria-hidden="true" />}</span>
    <span className={styles.identity}><strong>{state.account_name || (authorized ? "Google account" : "Google Workspace")}</strong><small>{state.account_label || "Connect your Google account"}</small></span>
    <button disabled={busy || !state.connection_supported} onClick={onConnect} type="button">{state.connected ? "Disconnect" : authorized ? "Finish connection" : "Connect"}</button>
  </section>;
}
