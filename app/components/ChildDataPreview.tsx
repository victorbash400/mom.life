import type { ChildDataNode } from "../types/childData";
import { PinkFolderIcon } from "./PinkFolderIcon";
import styles from "./ChildDataPreview.module.css";
export function ChildDataPreview({ node }: { node: ChildDataNode }) { return <aside className={styles.preview} aria-label={`${node.name} preview`}><PinkFolderIcon kind={node.kind} /><h2>{node.name}</h2>{node.value ? <strong>{node.value}</strong> : null}<small>{node.kind === "folder" ? "Folder" : "Information"}</small></aside>; }
