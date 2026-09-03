import Image from "next/image";
import { SquareCheckBig, UsersRound } from "lucide-react";
import styles from "./AppHeader.module.css";

export function AppHeader() {
  return <header className={styles.header}><button className={styles.greeting} type="button" aria-label="Open Sarah's profile"><Image src="/sarah-profile.png" alt="Sarah" width={44} height={44} priority /><span>Hi, Sarah</span></button><nav className={styles.actions} aria-label="Family controls"><button type="button" aria-label="Family"><UsersRound /></button><button type="button" aria-label="Things needing attention"><SquareCheckBig /></button></nav></header>;
}
