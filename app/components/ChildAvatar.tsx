import { children as demoChildren } from "../data/dashboard";
import type { ChildProfile } from "../types/dashboard";
export function childAvatarStyle(child: ChildProfile) {
  const demoChild = demoChildren.find(({ id }) => id === child.id);
  if (!child.has_photo && demoChild) {
    return { backgroundImage: 'url("/family-avatars.png")', backgroundSize: "200% 200%", backgroundPosition: demoChild.avatarPosition };
  }
  return { backgroundImage: `url("/api/family/children/${encodeURIComponent(child.id)}/${child.has_photo ? `photo?v=${child.photo_version}` : "avatar"}")`, backgroundSize: "cover", backgroundPosition: "center" };
}
