import type { ChildDataNode } from "../types/childData";
import { PinkFolderIcon } from "./PinkFolderIcon";
import styles from "./ChildDataList.module.css";

type ItemHandler = (node: ChildDataNode) => void;

export function ChildDataList({ nodes, selectedId, onOpen }: { nodes: ChildDataNode[]; selectedId?: string; onOpen: ItemHandler }) {
  return (
    <table className={styles.table}>
      <thead><tr><th>Name</th><th>Date Modified</th><th>Kind</th></tr></thead>
      <tbody>
        {nodes.map((node) => (
          <tr aria-selected={selectedId === node.id} key={node.id} onClick={() => onOpen(node)}>
            <td>
              <span className={styles.nameCell}>
                <PinkFolderIcon kind={node.kind} size="small" />
                <span>{node.name}</span>
              </span>
            </td>
            <td>{formatDate(node.updatedAt)}</td>
            <td>{kindLabel(node.kind)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatDate(value: string) {
  return dateFormatter.format(new Date(value));
}

function kindLabel(kind: ChildDataNode["kind"]) {
  return kind === "folder" ? "Folder" : kind === "profile" ? "Child profile" : `${kind[0].toUpperCase()}${kind.slice(1)}`;
}

const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
