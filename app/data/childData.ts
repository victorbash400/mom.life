import type { ChildProfile, PersonProfile } from "../types/dashboard";
import type { ChildDataNode } from "../types/childData";

export function profileData(profile: PersonProfile, child = false): ChildDataNode[] {
  const updatedAt = new Date().toISOString();
  const folders: ChildDataNode[] = [
    { id: "profile", parentId: null, name: "Profile", kind: "folder", updatedAt },
    { id: "health", parentId: null, name: "Health", kind: "folder", updatedAt },
    { id: "documents", parentId: null, name: "Documents", kind: "folder", updatedAt },
    { id: "activities", parentId: null, name: "Activities", kind: "folder", updatedAt },
  ];
  if (!child) return folders;
  const childProfile = profile as ChildProfile;
  return [...folders,
    { id: "school", parentId: null, name: "School", kind: "folder", updatedAt },
    { id: "routines", parentId: null, name: "Routines", kind: "folder", updatedAt },
    { id: "milestones", parentId: null, name: "Milestones", kind: "folder", updatedAt },
    { id: "age", parentId: "profile", name: "Age", kind: "profile", value: childProfile.age, updatedAt },
  ];
}
