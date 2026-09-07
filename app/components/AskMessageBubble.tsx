import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AskMessage } from "../types/chat";
import styles from "./AskMessageBubble.module.css";

export function AskMessageBubble({ message, pending }: { message: AskMessage; pending: boolean }) {
  return <article className={styles.message} data-role={message.role}>{pending ? <span className={styles.thinking}>Thinking</span> : message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : <p>{message.content}</p>}</article>;
}
