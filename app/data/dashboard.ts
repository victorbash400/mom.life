import type { ChildProfile, PersonProfile } from "../types/dashboard";

export const sarah: PersonProfile = { id: "sarah", name: "Sarah" };

export const children: Pick<ChildProfile, "id" | "name" | "age" | "color" | "avatarPosition">[] = [
  { id: "amina", name: "Amina", age: "8 years", color: "#d9caef", avatarPosition: "100% 0%" },
  { id: "noah", name: "Noah", age: "5 years", color: "#c7e2db", avatarPosition: "0% 100%" },
  { id: "lila", name: "Lila", age: "2 years", color: "#f4cfd5", avatarPosition: "100% 100%" },
];
