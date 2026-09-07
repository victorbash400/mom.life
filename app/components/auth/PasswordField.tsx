"use client";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import styles from "./PasswordField.module.css";

export function PasswordField({ value, onChange, disabled, create = false }: { value: string; onChange: (value: string) => void; disabled: boolean; create?: boolean }) {
  const [visible, setVisible] = useState(false);
  return <label>Password<span className={styles.field}><input type={visible ? "text" : "password"} name="password" autoComplete={create ? "new-password" : "current-password"} minLength={create ? 10 : undefined} placeholder={create ? "At least 10 characters" : undefined} required value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} /><button type="button" aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} onClick={() => setVisible(!visible)} disabled={disabled}>{visible ? <EyeOff /> : <Eye />}</button></span></label>;
}
