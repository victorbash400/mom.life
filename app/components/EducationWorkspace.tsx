import type { ChildProfile } from "../types/dashboard";
import { useEducation } from "../hooks/useEducation";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./EducationWorkspace.module.css";

export function EducationWorkspace({ child, onClose }: { child?: ChildProfile; onClose: () => void }) {
  const education = useEducation();
  if (!child) return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} /><div className={styles.empty}>Add a child to view education</div></section>;
  const snapshot = education.snapshots.find((item) => item.child_id === child.id);
  return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} />{education.error ? <p className={styles.error} role="alert">{education.error}</p> : null}<article className={styles.snapshot}><header><h2>{child.name}</h2><small>{child.age}</small></header>{education.loaded ? <p>{snapshot?.summary || "No education snapshot yet."}</p> : null}{snapshot ? <time dateTime={snapshot.updated_at}>Updated {new Date(snapshot.updated_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</time> : <small>The Education Agent will update this from confirmed school information.</small>}</article></section>;
}
