"use client";
import styles from "./SignOutButton.module.css";
import { useRouter } from "next/navigation";
import { useState } from "react";
export function SignOutButton() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function signOut() {
    setBusy(true);
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Could not sign out. Please try again.");
      router.replace("/sign-in"); router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not sign out."); setBusy(false); }
  }
  return <div className={styles.signout}><button type="button" onClick={signOut} disabled={busy}>{busy ? "Signing out…" : "Sign out"}</button>{error ? <p role="alert">{error}</p> : null}</div>;
}
