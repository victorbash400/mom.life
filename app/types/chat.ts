export type ToolMessage = { id: string; kind: "tool"; name: string; status: "running" | "done" | "error" };
export type AskMessage = { id: string; kind?: "message"; role: "user" | "assistant"; content: string } | ToolMessage;
export type ChatStreamEvent =
  | { type: "content"; content: string }
  | { type: "tool_call"; id: string; name: string; args: Record<string, unknown> }
  | { type: "tool_response"; id: string; name: string; status: "done" | "error" }
  | { type: "done" }
  | { type: "error"; error: string };
export type ChatSummary = { id: string; title: string; updated_at: number };
export type Chat = ChatSummary & { messages: AskMessage[] };
