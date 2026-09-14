import { SendHorizontal } from "lucide-react";
import { useState } from "react";
import type { SimulatorProfile } from "../types/simulator";
import styles from "./SimulatorWhatsApp.module.css";

type Props = { connected: boolean; profile: SimulatorProfile; send: (profileId: string, text: string, sender?: string) => Promise<void> };
export function SimulatorMessageComposer({ connected, profile, send }: Props) {
  const [reply, setReply] = useState(profile.role === "adult");
  const [sender, setSender] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit() {
    if (busy || !text.trim() || (!reply && !sender.trim())) return;
    setBusy(true);
    try { await send(profile.id, text.trim(), reply ? undefined : sender.trim()); setText(""); }
    catch { /* The simulator displays the request error; retain the draft. */ }
    finally { setBusy(false); }
  }
  return <div className={styles.composer}>
    <div className={styles.origin}><select aria-label="Message type" disabled={busy} onChange={(event) => setReply(event.target.value === "reply")} value={reply ? "reply" : "inbox"}>
      <option value="inbox">Incoming message</option><option value="reply">Reply as {profile.name}</option>
    </select>{!reply && <input aria-label="Message sender" disabled={busy} maxLength={128} onChange={(event) => setSender(event.target.value)} placeholder="From" value={sender} />}</div>
    <form onSubmit={(event) => { event.preventDefault(); void submit(); }}><input aria-label="Simulated WhatsApp message" disabled={!connected || busy} onChange={(event) => setText(event.target.value)} placeholder={connected ? reply ? "Reply to mom.life" : `Message to ${profile.name}` : "Connect WhatsApp Simulator"} value={text} /><button aria-label={reply ? "Send simulated reply" : "Receive simulated message"} disabled={!connected || busy || !text.trim() || (!reply && !sender.trim())} type="submit"><SendHorizontal aria-hidden="true" /></button></form>
  </div>;
}
