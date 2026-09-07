"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { PasswordField } from "./PasswordField";
import styles from "./LoginForm.module.css";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not sign in.");
      router.replace("/"); router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not sign in."); setBusy(false); }
  }
  return <form className={styles.form} onSubmit={submit}>
    <label>Email<input type="email" name="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={busy} /></label>
    <PasswordField value={password} onChange={setPassword} disabled={busy} />
    <div className={styles.feedback} aria-live="polite">{error ? <p role="alert">{error}</p> : <button type="button" disabled={busy} onClick={() => { setEmail("demo@mom.life"); setPassword("MomLifeDemo!"); }}>Demo</button>}</div>
    <button className={styles.submit} type="submit" disabled={busy}>{busy ? "Logging in…" : "Log in"}</button>
  </form>;
}
