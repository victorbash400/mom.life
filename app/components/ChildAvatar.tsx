import type { ChildProfile } from "../types/dashboard";
export function childAvatarStyle(child: ChildProfile) {
  return { backgroundImage: `url("/api/family/children/${encodeURIComponent(child.id)}/${child.has_photo ? `photo?v=${child.photo_version}` : "avatar"}")`, backgroundSize: "cover", backgroundPosition: "center" };
}
