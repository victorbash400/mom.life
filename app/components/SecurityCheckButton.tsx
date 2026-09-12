import { useState } from "react";
export function SecurityCheckButton({ disabled }: { disabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function check() {
    setBusy(true);
    try {
      const response = await fetch("/api/security/check", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not start safety checks.");
      setMessage(`${payload.queued} reviews queued using saved settings`);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Could not start safety checks."); }
    finally { setBusy(false); }
  }
  return <footer><small role="status">{message}</small><button disabled={disabled || busy} onClick={() => void check()} type="button">{busy ? "Checking…" : "Check recent information"}</button></footer>;
}
