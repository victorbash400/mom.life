"use client";

import { useMemo, useState } from "react";
import { childData } from "../data/childData";
import type { ChildProfile } from "../types/dashboard";
import type { ChildDataNode, ChildDataSort, ChildDataView } from "../types/childData";
import { ChildDataColumns } from "./ChildDataColumns";
import { ChildDataGrid } from "./ChildDataGrid";
import { ChildDataList } from "./ChildDataList";
import { ChildDataToolbar } from "./ChildDataToolbar";
import styles from "./ChildInformationWorkspace.module.css";

export function ChildInformationWorkspace({ child, onBack }: { child: ChildProfile; onBack: () => void }) {
  const nodes = useMemo(() => childData(child), [child]);
  const [folderId, setFolderId] = useState<string>();
  const [selectedId, setSelectedId] = useState<string>();
  const [view, setView] = useState<ChildDataView>("grid");
  const [sort, setSort] = useState<ChildDataSort>("name-asc");
  const [query, setQuery] = useState("");
  const folder = nodes.find((node) => node.id === folderId);
  const selected = nodes.find((node) => node.id === selectedId);
  const visible = nodes
    .filter((node) => node.parentId === (folderId ?? null) && (!query || node.name.toLowerCase().includes(query.toLowerCase())))
    .sort((left, right) => sort === "name-desc" ? right.name.localeCompare(left.name) : left.name.localeCompare(right.name));

  function open(node: ChildDataNode) {
    if (node.kind === "folder") {
      setFolderId(node.id);
      setSelectedId(undefined);
    } else {
      setSelectedId(node.id);
    }
  }

  function back() {
    if (folderId) {
      setFolderId(undefined);
      setSelectedId(undefined);
    } else {
      onBack();
    }
  }

  function root() {
    setFolderId(undefined);
    setSelectedId(undefined);
  }

  function changeView(next: ChildDataView) {
    setView(next);
    setSelectedId(undefined);
  }

  return <section className={styles.information}><ChildDataToolbar canGoBack childName={child.name} folderName={folder?.name} onBack={back} onQueryChange={setQuery} onRoot={root} onSortChange={setSort} onViewChange={changeView} query={query} sort={sort} view={view} /><section className={styles.content}>{view === "grid" ? <ChildDataGrid nodes={visible} onOpen={open} /> : null}{view === "list" ? <ChildDataList nodes={visible} onOpen={open} selectedId={selectedId} /> : null}{view === "columns" ? <ChildDataColumns nodes={nodes} onSelect={(node) => setSelectedId(node.id)} selected={selected} /> : null}</section></section>;
}
