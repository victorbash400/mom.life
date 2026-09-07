"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { PasswordField } from "./PasswordField";
import styles from "./LoginForm.module.css";
export function RegistrationForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name"), email: data.get("email"), password }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not create account.");
      router.replace("/"); router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create account."); setBusy(false); }
  }
  return <form className={styles.form} onSubmit={submit}><label>Name<input name="name" autoComplete="name" required maxLength={100} disabled={busy} /></label><label>Email<input name="email" type="email" autoComplete="username" required disabled={busy} /></label><PasswordField value={password} onChange={setPassword} disabled={busy} create /><div className={styles.feedback} aria-live="polite">{error ? <p role="alert">{error}</p> : null}</div><button className={styles.submit} disabled={busy || password.length < 10} type="submit">{busy ? "Creating…" : "Create account"}</button></form>;
}
