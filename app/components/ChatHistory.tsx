import { PanelLeftClose, Search, SquarePen, Trash2 } from "lucide-react";
import { useState } from "react";
import type { ChatSummary } from "../types/chat";
import styles from "./ChatHistory.module.css";

type Props = { open: boolean; chats: ChatSummary[]; activeId?: string; disabled: boolean; onClose: () => void; onNew: () => void; onSelect: (id: string) => void; onDelete: (id: string) => void };
export function ChatHistory({ open, chats, activeId, disabled, onClose, onNew, onSelect, onDelete }: Props) {
  const [query, setQuery] = useState("");
  const filtered = chats.filter((chat) => chat.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <aside aria-hidden={!open} inert={!open ? true : undefined} data-open={open} className={styles.sidebar} id="chat-history" aria-label="Chat history"><div className={styles.content}>
    <header><strong>Chats</strong><button type="button" aria-label="Close chats" onClick={onClose}><PanelLeftClose /></button></header>
    <button className={styles.create} type="button" disabled={disabled} onClick={onNew}><SquarePen />New chat</button>
    <label className={styles.search}><Search /><input type="search" aria-label="Search chats" placeholder="Search chats" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
    <nav aria-label="Past chats">{filtered.map((chat) => <div className={styles.row} data-active={chat.id === activeId} key={chat.id}><button type="button" disabled={disabled} title={chat.title} aria-current={chat.id === activeId ? "page" : undefined} onClick={() => onSelect(chat.id)}>{chat.title}</button><button type="button" disabled={disabled} aria-label={`Delete ${chat.title}`} onClick={() => onDelete(chat.id)}><Trash2 /></button></div>)}{!filtered.length ? <p>{query ? "No matching chats" : "No past chats"}</p> : null}</nav>
  </div></aside>;
}
