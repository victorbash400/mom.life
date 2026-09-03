"use client";

import { useRef, useState } from "react";
import { AskComposer } from "./AskComposer";
import { AskMessageList } from "./AskMessageList";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./AskWorkspace.module.css";

export type AskMessage = { id: string; role: "user" | "assistant"; content: string };

export function AskWorkspace({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<AskMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const chatId = useRef(crypto.randomUUID());

  async function send(message: string) {
    const userMessage: AskMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const assistantId = crypto.randomUUID();
    setMessages((current) => [...current, userMessage, { id: assistantId, role: "assistant", content: "" }]);
    setSending(true);
    setError("");
    try {
      const response = await fetch("/api/chat/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ family_id: "sarah-family", chat_id: chatId.current, message }) });
      if (!response.ok || !response.body) throw new Error(`mom.life could not respond (${response.status})`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) applyEvent(part, assistantId, setMessages);
      }
      if (buffer.trim()) applyEvent(buffer, assistantId, setMessages);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "mom.life could not respond");
      setMessages((current) => current.filter(({ id }) => id !== assistantId || current.find((item) => item.id === id)?.content));
    } finally { setSending(false); }
  }

  return <div className={styles.workspace}><WorkspaceHeader title="Ask" subtitle="Your family assistant" onClose={onClose} /><AskMessageList messages={messages} sending={sending} />{error ? <p className={styles.error} role="alert">{error}</p> : null}<AskComposer disabled={sending} onSend={send} /></div>;
}

function applyEvent(raw: string, assistantId: string, setMessages: React.Dispatch<React.SetStateAction<AskMessage[]>>) {
  const data = raw.split("\n").find((line) => line.startsWith("data:"))?.slice(5).trim();
  if (!data) return;
  const event = JSON.parse(data) as { type?: string; content?: string; error?: string };
  if (event.type === "error") throw new Error(event.error ?? "mom.life could not respond");
  if (!event.content) return;
  setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, content: item.content + event.content } : item));
}
