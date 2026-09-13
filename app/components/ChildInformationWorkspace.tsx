"use client";

import { useEffect, useState, useCallback } from "react";
import { FolderActions } from "./FolderActions";
import type { PersonProfile } from "../types/dashboard";
import type { ChildDataNode, ChildDataSort, ChildDataView } from "../types/childData";
import { ChildDataColumns } from "./ChildDataColumns";
import { ChildDataGrid } from "./ChildDataGrid";
import { ChildDataList } from "./ChildDataList";
import { ChildDataToolbar } from "./ChildDataToolbar";
import { LoadingIndicator } from "./LoadingIndicator";
import styles from "./ChildInformationWorkspace.module.css";

export function ChildInformationWorkspace({ profile, child = false, onBack }: { profile: PersonProfile; child?: boolean; onBack: () => void }) {
  const ownerId = child ? profile.id : "parent";
  const [folderId, setFolderId] = useState<string>();
  const [nodes, setNodes] = useState<ChildDataNode[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const refresh = useCallback(async () => {
    const response = await fetch(`/api/family/children/${ownerId}/nodes`, { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load files.");
    const next: ChildDataNode[] = await response.json();
    setNodes(next); setLoaded(true);
    setFolderId((current) => next.some((node) => node.id === current) ? current : undefined);
    setError("");
  }, [ownerId]);
  useEffect(() => { const frame = requestAnimationFrame(() => { void refresh().catch((cause) => setError(cause.message)); }); return () => cancelAnimationFrame(frame); }, [refresh]);
  const [selectedId, setSelectedId] = useState<string>();
  const [view, setView] = useState<ChildDataView>("grid");
  const [sort, setSort] = useState<ChildDataSort>("name-asc");
  const [query, setQuery] = useState("");
  const folder = nodes.find((node) => node.id === folderId);
  const selected = nodes.find((node) => node.id === selectedId);
  const visible = nodes
    .filter((node) => node.parentId === (folderId ?? null) && (!query || node.name.toLowerCase().includes(query.toLowerCase())))
    .sort((left, right) => sort.startsWith("date") ? (new Date(left.updatedAt).getTime() - new Date(right.updatedAt).getTime()) * (sort === "date-desc" ? -1 : 1) : sort === "name-desc" ? right.name.localeCompare(left.name) : left.name.localeCompare(right.name));

  function open(node: ChildDataNode) {
    if (node.kind === "folder") {
      setFolderId(node.id);
      setSelectedId(node.id);
    } else {
      setSelectedId(node.id);
    }
  }

  function back() {
    if (folderId) {
      setFolderId(folder?.parentId ?? undefined);
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

  return <section className={styles.information}><ChildDataToolbar canGoBack childName={profile.name} folderName={folder?.name} onBack={back} onQueryChange={setQuery} onRoot={root} onSortChange={setSort} onViewChange={changeView} query={query} sort={sort} view={view} /><section className={styles.content}>{error ? <p role="alert">{error}</p> : !loaded ? <LoadingIndicator /> : <><FolderActions childId={ownerId} parentId={folderId} selected={selected} onSaved={async () => { await refresh(); setSelectedId(undefined); }} />{view === "grid" ? <ChildDataGrid nodes={visible} onOpen={open} /> : null}{view === "list" ? <ChildDataList nodes={visible} onOpen={open} selectedId={selectedId} /> : null}{view === "columns" ? <ChildDataColumns nodes={nodes} onSelect={open} selected={selected} /> : null}</>}</section></section>;
}
