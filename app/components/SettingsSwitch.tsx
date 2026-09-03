import styles from "./SettingsSwitch.module.css";
export function SettingsSwitch({ checked, label, onChange }: { checked: boolean; label: string; onChange: (checked: boolean) => void }) { return <label className={styles.switch}><input aria-label={label} checked={checked} onChange={(event) => onChange(event.target.checked)} type="checkbox" /><span /></label>; }
