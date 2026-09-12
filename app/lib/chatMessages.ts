import type { AskMessage, ChatStreamEvent } from "../types/chat";

export function applyChatEvent(messages: AskMessage[], event: ChatStreamEvent): AskMessage[] {
  if (event.type === "tool_call") {
    if (messages.some((item) => item.kind === "tool" && item.id === event.id)) return messages;
    return [...messages, { id: event.id, kind: "tool", name: event.name, status: "running" }];
  }
  if (event.type === "tool_response") {
    return messages.map((item) => item.kind === "tool" && item.id === event.id ? { ...item, status: event.status } : item);
  }
  if (event.type === "content") {
    const last = messages.at(-1);
    if (last && last.kind !== "tool" && last.role === "assistant") {
      return messages.map((item) => item === last ? { ...last, content: last.content + event.content } : item);
    }
    return [...messages, { id: crypto.randomUUID(), role: "assistant", content: event.content }];
  }
  if (event.type === "done" || event.type === "error") {
    return messages.map((item) => item.kind === "tool" && item.status === "running" ? { ...item, status: "error" as const } : item);
  }
  return messages;
}
