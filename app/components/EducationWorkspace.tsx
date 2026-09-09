import type { ChildProfile } from "../types/dashboard";
import { educationOverview } from "../data/education";
import { EducationProgressTable } from "./EducationProgressTable";
import { EducationSummary } from "./EducationSummary";
import { EducationUpcomingList } from "./EducationUpcomingList";
import { WorkspaceHeader } from "./WorkspaceHeader";
import styles from "./EducationWorkspace.module.css";

export function EducationWorkspace({ child, onClose }: { child?: ChildProfile; onClose: () => void }) {
  if (!child) return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} /><div className={styles.empty}>Add a child to view education</div></section>;
  const overview = educationOverview(child);
  return <section className={styles.workspace}><WorkspaceHeader title="Education" onClose={onClose} /><section className={styles.panel}><header><strong>{child.name}</strong><small>{child.age}</small></header><EducationSummary overview={overview} /><div className={styles.details}><EducationProgressTable subjects={overview.subjects} /><EducationUpcomingList items={overview.upcoming} /></div></section></section>;
}
