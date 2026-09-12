import { AskToolIndicator } from "./AskToolIndicator";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AskMessage } from "../types/chat";
import styles from "./AskMessageBubble.module.css";

export function AskMessageBubble({ message, streaming }: { message: AskMessage; streaming: boolean }) {
  if (message.kind === "tool") return <AskToolIndicator item={message} />;
  return <article className={styles.message} data-role={message.role}>{streaming && !message.content ? <span className={styles.thinking}>Thinking</span> : message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : <p>{message.content}</p>}</article>;
}
