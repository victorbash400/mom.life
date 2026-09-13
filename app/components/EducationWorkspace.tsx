import type { ChildProfile } from "../types/dashboard";
import { useEducation } from "../hooks/useEducation";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { EducationSourceLinks } from "./EducationSourceLinks";
import { LoadingIndicator } from "./LoadingIndicator";
import styles from "./EducationWorkspace.module.css";

export function EducationWorkspace({ child, onClose, onSourceSelect }: { child?: ChildProfile; onClose: () => void; onSourceSelect: (id: string) => void }) {
  const education = useEducation();
  if (!child) return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} /><div className={styles.empty}>Add a child to view education</div></section>;
  const snapshot = education.snapshots.find((item) => item.child_id === child.id);
  return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} />{education.error ? <p className={styles.error} role="alert">{education.error}</p> : null}{education.loaded ? <article className={styles.snapshot}><header><h2>{child.name}</h2><small>{child.age}</small></header><p>{snapshot?.summary || "No education snapshot yet."}</p>{snapshot ? <><time dateTime={snapshot.updated_at}>Updated {new Date(snapshot.updated_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</time><EducationSourceLinks onSelect={onSourceSelect} sourceIds={snapshot.source_ids} /></> : <small>The Education Agent will update this from confirmed school information.</small>}</article> : !education.error ? <LoadingIndicator /> : null}</section>;
}
