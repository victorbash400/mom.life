import { CalendarDays, GraduationCap, Heart, Mail, ShoppingCart } from "lucide-react";
import styles from "./UtilityNav.module.css";

const utilities = [{ label: "Messages", icon: Mail }, { label: "Health", icon: Heart }, { label: "School", icon: GraduationCap }, { label: "Calendar", icon: CalendarDays }, { label: "Shopping", icon: ShoppingCart }];

export function UtilityNav() {
  return <nav className={styles.nav} aria-label="Family areas">{utilities.map(({ label, icon: Icon }) => <button type="button" key={label} aria-label={label} title={label}><Icon /></button>)}</nav>;
}
