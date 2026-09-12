import { useEffect, useRef } from "react";
import type { AskMessage } from "../types/chat";
import { AskMessageBubble } from "./AskMessageBubble";
import styles from "./AskMessageList.module.css";

export function AskMessageList({ messages, sending }: { messages: AskMessage[]; sending: boolean }) {
  const list = useRef<HTMLElement>(null);
  const follow = useRef(true);
  useEffect(() => { if (follow.current && list.current) list.current.scrollTop = list.current.scrollHeight; }, [messages]);
  return <section ref={list} onScroll={() => { const node = list.current; if (node) follow.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80; }} className={styles.list} aria-live="polite"><div>{messages.map((message) => {
    const streaming = sending && message === messages.at(-1) && message.kind !== "tool" && message.role === "assistant";
    return <AskMessageBubble key={message.id} message={message} streaming={streaming} />;
  })}</div></section>;
}
