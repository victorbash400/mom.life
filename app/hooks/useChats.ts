"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat } from "../lib/chatStream";
import type { Chat, ChatSummary } from "../types/chat";

async function request<T>(path = "", method = "GET"): Promise<T> {
  const response = await fetch(`/api/chats${path}`, { method });
  if (!response.ok) throw new Error((await response.json()).error ?? "Could not load chats.");
  return response.status === 204 ? undefined as T : response.json();
}

export function useChats(familyId: string) {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [active, setActive] = useState<Chat | null>(null);
  const [busy, setBusy] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const refresh = useCallback(async () => setChats(await request<ChatSummary[]>()), []);
  useEffect(() => {
    let live = true;
    request<ChatSummary[]>().then((items) => { if (live) setChats(items); }).catch((cause) => { if (live) setError(cause.message); }).finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [familyId]);

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
      const chat = active ?? await request<Chat>("", "POST");
      const assistantId = crypto.randomUUID();
      setActive({ ...chat, title: chat.messages.length ? chat.title : message.replace(/\s+/g, " ").slice(0, 70), messages: [...chat.messages, { id: crypto.randomUUID(), role: "user", content: message }, { id: assistantId, role: "assistant", content: "" }] });
      setSending(true);
      try {
        await streamChat(familyId, chat.id, message, (content) => setActive((current) => current ? { ...current, messages: current.messages.map((item) => item.id === assistantId ? { ...item, content: item.content + content } : item) } : current));
      } finally {
        setSending(false);
        setActive((current) => current ? { ...current, messages: current.messages.filter((item) => item.id !== assistantId || item.content) } : current);
        await refresh();
      }
    });
  }
  return { chats, active, busy, sending, error, select, create, remove, send };
}
