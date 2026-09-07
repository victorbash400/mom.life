export type AskMessage = { id: string; role: "user" | "assistant"; content: string };
export type ChatSummary = { id: string; title: string; updated_at: number };
export type Chat = ChatSummary & { messages: AskMessage[] };
