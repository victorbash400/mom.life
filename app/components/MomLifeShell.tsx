import { ActionPanel } from "./ActionPanel";
import { AppHeader } from "./AppHeader";
import { ChildSwitcher } from "./ChildSwitcher";
import styles from "./MomLifeShell.module.css";

export function MomLifeShell() {
  return <main className={styles.shell}><AppHeader /><ChildSwitcher /><ActionPanel /></main>;
}
