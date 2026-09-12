import type { ChatStreamEvent } from "../types/chat";

export async function streamChat(chatId: string, message: string, onEvent: (event: ChatStreamEvent) => void) {
  const response = await fetch("/api/chat/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: chatId, message }) });
  if (!response.ok || !response.body) throw new Error("mom.life could not respond. Please try again.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", completed = false;
  function apply(raw: string) {
    const data = raw.split("\n").find((line) => line.startsWith("data:"))?.slice(5).trim();
    if (!data) return;
    const event = JSON.parse(data) as ChatStreamEvent;
    if (event.type === "error") throw new Error(event.error ?? "mom.life could not respond.");
    if (event.type === "done") completed = true;
    onEvent(event);
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      parts.forEach(apply);
    }
    if (buffer.trim()) apply(buffer);
    if (!completed) throw new Error("The response was interrupted. Please try again.");
  } finally { reader.releaseLock(); }
}
