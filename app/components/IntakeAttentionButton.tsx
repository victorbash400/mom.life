import { Bell } from "lucide-react";
import styles from "./IntakeAttentionButton.module.css";

export function IntakeAttentionButton({ count, onClick }: { count: number; onClick: () => void }) {
  return <button aria-label={`${count} incoming ${count === 1 ? "item needs" : "items need"} attention`} className={styles.button} onClick={onClick} title="Incoming items needing attention" type="button"><Bell aria-hidden="true" />{count ? <i /> : null}</button>;
}
