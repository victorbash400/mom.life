import type { ChildDataNode } from "../types/childData";
import { PinkFolderIcon } from "./PinkFolderIcon";
import styles from "./ChildDataGrid.module.css";
export function ChildDataGrid({ nodes, onOpen }: { nodes: ChildDataNode[]; onOpen: (node: ChildDataNode) => void }) { return <section className={styles.grid} aria-label="Information items">{nodes.map((node) => <button key={node.id} onClick={() => onOpen(node)} type="button"><PinkFolderIcon kind={node.kind} /><strong>{node.name}</strong>{node.value ? <small>{node.value}</small> : null}</button>)}</section>; }
