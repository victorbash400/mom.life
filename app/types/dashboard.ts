export type ViewId = "today" | "needs-you" | "handled" | "calendar" | "memory" | "connections";

export interface PersonProfile {
  id: string;
  name: string;
}

export interface ChildProfile extends PersonProfile {
  birth_date: string | null;
  email_updates: boolean;
  text_updates: boolean;
  notifications: boolean;
  photo_version: number;
  has_photo: boolean;
  avatar_seed: string;
  age: string;
  color: string;
  avatarPosition: string;
}
