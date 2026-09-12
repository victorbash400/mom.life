"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { applyChatEvent } from "../lib/chatMessages";
import { streamChat } from "../lib/chatStream";
import type { Chat, ChatSummary } from "../types/chat";

async function request<T>(path = "", method = "GET"): Promise<T> {
  const response = await fetch(`/api/chats${path}`, { method });
  if (!response.ok) throw new Error((await response.json()).error ?? "Could not load chats.");
  return response.status === 204 ? undefined as T : response.json();
}

export function useChats() {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [active, setActive] = useState<Chat | null>(null);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const refresh = useCallback(async () => setChats(await request<ChatSummary[]>()), []);
  useEffect(() => {
    let live = true;
    request<ChatSummary[]>().then((items) => { if (live) setChats(items); }).catch((cause) => { if (live) setError(cause.message); });
    return () => { live = false; };
  }, []);

  async function perform(action: () => Promise<void>) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try { await action(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update chat."); }
    finally { locked.current = false; setBusy(false); }
  }
  function select(id: string) { return perform(async () => setActive(await request<Chat>(`/${id}`))); }
  function create() { if (!locked.current) { setActive(null); setError(""); } }
  function remove(id: string) { return perform(async () => { await request(`/${id}`, "DELETE"); setChats((items) => items.filter((item) => item.id !== id)); if (active?.id === id) setActive(null); }); }
  function send(message: string) {
    return perform(async () => {
      const chat = active ?? { id: crypto.randomUUID(), title: message.replace(/\s+/g, " ").slice(0, 70), updated_at: Date.now(), messages: [] };
      const assistantId = crypto.randomUUID();
      setActive({ ...chat, title: chat.messages.length ? chat.title : message.replace(/\s+/g, " ").slice(0, 70), messages: [...chat.messages, { id: crypto.randomUUID(), role: "user", content: message }, { id: assistantId, role: "assistant", content: "" }] });
      setSending(true);
      try {
        await streamChat(chat.id, message, (event) => setActive((current) => current ? { ...current, messages: applyChatEvent(current.messages.filter((item) => item.kind === "tool" || item.id !== assistantId || item.content), event) } : current));
      } catch (cause) {
        setActive((current) => current ? { ...current, messages: applyChatEvent(current.messages, { type: "error", error: String(cause) }) } : current);
        throw cause;
      } finally {
        setSending(false);
        setActive((current) => current ? { ...current, messages: current.messages.filter((item) => item.kind === "tool" || item.id !== assistantId || item.content) } : current);
        void refresh().catch((cause) => setError(cause instanceof Error ? cause.message : "Could not refresh chat history."));
      }
    });
  }
  return { chats, active, busy, sending, error, select, create, remove, send };
}
