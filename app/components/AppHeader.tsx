import Image from "next/image";
import styles from "./AppHeader.module.css";

export function AppHeader({ pluginsOpen, onPluginsToggle }: { pluginsOpen: boolean; onPluginsToggle: () => void }) {
  return <header className={styles.header}><button className={styles.greeting} type="button" aria-label="Open Sarah's profile"><Image src="/sarah-profile.png" alt="Sarah" width={44} height={44} priority /><span>Hi, Sarah</span></button><nav className={styles.actions} aria-label="Family controls"><button type="button" aria-label="Children"><Image className={styles.assetIcon} src="/kid-svgrepo-com.svg" alt="" width={38} height={38} /></button><button aria-expanded={pluginsOpen} onClick={onPluginsToggle} type="button" aria-label="Connections"><Image className={styles.assetIcon} src="/plugin-svgrepo-com.svg" alt="" width={35} height={35} /></button></nav></header>;
}
