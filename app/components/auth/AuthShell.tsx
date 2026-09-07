import { RegistrationForm } from "./RegistrationForm";
import Link from "next/link";
import { AuthSurface } from "./AuthSurface";
import { LoginForm } from "./LoginForm";
import styles from "./AuthShell.module.css";

export function AuthShell({ mode }: { mode: "login" | "signup" }) {
  return <main className={styles.page}><section className={styles.shell} aria-labelledby="auth-title"><AuthSurface /><div className={styles.content}>
    <h1 id="auth-title" className={styles.brand}>mom.<em>life</em></h1>
    <nav className={styles.tabs} aria-label="Account access"><Link href="/sign-in" aria-current={mode === "login" ? "page" : undefined}>Log in</Link><Link href="/sign-up" aria-current={mode === "signup" ? "page" : undefined}>Create account</Link></nav>
    <div className={styles.formArea}>{mode === "login" ? <LoginForm /> : <RegistrationForm />}</div>
  </div></section></main>;
}
