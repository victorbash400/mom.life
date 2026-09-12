"use client";
import { AskChatHeader } from "./AskChatHeader";
import { useState } from "react";
import { useChats } from "../hooks/useChats";
import { AskComposer } from "./AskComposer";
import { AskMessageList } from "./AskMessageList";
import { ChatHistory } from "./ChatHistory";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./AskWorkspace.module.css";

export function AskWorkspace({ onClose }: { onClose: () => void }) {
  const chat = useChats();
  const [historyOpen, setHistoryOpen] = useState(false);
  return <div className={styles.workspace}>
    <WorkspaceHeader title="Ask" onClose={onClose} />
    <div className={styles.body} data-history={historyOpen}>
      <ChatHistory open={historyOpen} chats={chat.chats} activeId={chat.active?.id} disabled={chat.busy} onClose={() => setHistoryOpen(false)} onNew={chat.create} onSelect={(id) => void chat.select(id)} onDelete={(id) => void chat.remove(id)} />
      <section className={styles.conversation} aria-label={chat.active?.title ?? "New chat"}>
        <AskChatHeader title={chat.active?.title ?? "New chat"} historyOpen={historyOpen} onToggle={() => setHistoryOpen((open) => !open)} />
        <AskMessageList key={chat.active?.id ?? "new"} messages={chat.active?.messages ?? []} sending={chat.sending} />
        {chat.error ? <p className={styles.error} role="alert">{chat.error}</p> : null}
        <AskComposer disabled={chat.busy} onSend={chat.send} />
      </section>
    </div>
  </div>;
}
