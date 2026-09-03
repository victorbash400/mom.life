export type ChildDataView = "grid" | "list" | "columns";
export type ChildDataSort = "name-asc" | "name-desc" | "date-desc" | "date-asc";
export type ChildDataKind = "folder" | "profile" | "note";
export type ChildDataNode = { id: string; parentId: string | null; name: string; kind: ChildDataKind; value?: string; updatedAt: string };
