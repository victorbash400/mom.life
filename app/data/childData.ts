import type { ChildProfile } from "../types/dashboard";
import type { ChildDataNode } from "../types/childData";
export function childData(child: ChildProfile): ChildDataNode[] {
  const updatedAt = new Date().toISOString();
  return [
    { id: "profile", parentId: null, name: "Profile", kind: "folder", updatedAt },
    { id: "health", parentId: null, name: "Health", kind: "folder", updatedAt },
    { id: "school", parentId: null, name: "School", kind: "folder", updatedAt },
    { id: "documents", parentId: null, name: "Documents", kind: "folder", updatedAt },
    { id: "routines", parentId: null, name: "Routines", kind: "folder", updatedAt },
    { id: "milestones", parentId: null, name: "Milestones", kind: "folder", updatedAt },
    { id: "activities", parentId: null, name: "Activities", kind: "folder", updatedAt },
    { id: "age", parentId: "profile", name: "Age", kind: "profile", value: child.age, updatedAt },
  ];
}
