import { PanelLeft } from "lucide-react";
import styles from "./AskChatHeader.module.css";

export function AskChatHeader({ title, historyOpen, onToggle }: { title: string; historyOpen: boolean; onToggle: () => void }) {
  return <header className={styles.header}><button type="button" aria-label={historyOpen ? "Hide chats" : "Open chats"} title={historyOpen ? "Hide chats" : "Open chats"} aria-expanded={historyOpen} aria-controls="chat-history" onClick={onToggle}><PanelLeft aria-hidden="true" /></button><strong title={title}>{title}</strong></header>;
}
