import { useEffect, useRef } from "react";
import type { SimulatorMessage } from "../types/simulator";
import styles from "./SimulatorWhatsApp.module.css";

export function SimulatorMessageList({ messages, profileName }: { messages: SimulatorMessage[]; profileName: string }) {
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => { if (list.current) list.current.scrollTop = list.current.scrollHeight; }, [messages.length, profileName]);
  return <div aria-live="polite" className={styles.messages} ref={list}>{messages.length ? messages.map((message) => <article data-direction={message.direction === "incoming" && !message.inbox_message ? "outgoing" : "incoming"} key={message.id}>
    <small>{message.direction === "outgoing" ? "mom.life" : message.sender || profileName}</small><p>{message.body}</p>
  </article>) : <p className={styles.empty}>No messages</p>}</div>;
}
