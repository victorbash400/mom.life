import type { AskMessage } from "./AskWorkspace";
import { AskMessageBubble } from "./AskMessageBubble";
import styles from "./AskMessageList.module.css";

export function AskMessageList({ messages, sending }: { messages: AskMessage[]; sending: boolean }) {
  return <section className={styles.list} aria-live="polite"><div>{messages.map((message) => <AskMessageBubble key={message.id} message={message} pending={sending && message === messages.at(-1) && !message.content} />)}</div></section>;
}
