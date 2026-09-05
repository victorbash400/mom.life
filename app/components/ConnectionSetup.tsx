import styles from "./ConnectionSetup.module.css";
export function ConnectionSetup({ fields }: { fields: { name: string; configured: boolean }[] }) {
  return <details className={styles.setup}><summary>Connection setup</summary><p>Configure these values in the backend environment, then check the connection. Authorized provider credentials stay on the server.</p><ul>{fields.map((field) => <li key={field.name}><code>{field.name}</code><span>{field.configured ? "Configured" : "Required"}</span></li>)}</ul></details>;
}
