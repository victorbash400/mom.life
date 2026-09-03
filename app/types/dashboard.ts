export type ViewId = "today" | "needs-you" | "handled" | "calendar" | "memory" | "connections";

export interface PersonProfile {
  id: string;
  name: string;
}

export interface ChildProfile extends PersonProfile {
  age: string;
  color: string;
  avatarPosition: string;
}
