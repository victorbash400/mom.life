import { Link } from "lucide-react";
import styles from "./EducationSourceLinks.module.css";

export function EducationSourceLinks({ sourceIds, onSelect }: { sourceIds: string[]; onSelect: (id: string) => void }) {
  return <div className={styles.sources}>{sourceIds.map((id, index) => <button key={id} onClick={() => onSelect(id)} type="button"><Link size={12} />{sourceIds.length === 1 ? "Source" : `Source ${index + 1}`}</button>)}</div>;
}
