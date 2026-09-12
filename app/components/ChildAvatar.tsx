import type { ChildProfile } from "../types/dashboard";

export function childAvatarUrl(child: ChildProfile) {
  return `/api/family/children/${encodeURIComponent(child.id)}/${child.has_photo ? `photo?v=${child.photo_version}` : "avatar"}`;
}

export function childAvatarStyle(child: ChildProfile) {
  return { backgroundImage: `url("${childAvatarUrl(child)}")`, backgroundSize: "cover", backgroundPosition: "center" };
}
