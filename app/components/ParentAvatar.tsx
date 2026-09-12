import Image from "next/image";
import { UserRound } from "lucide-react";
import type { PersonProfile } from "../types/dashboard";

export function ParentAvatar({ parent, size }: { parent: PersonProfile; size: number }) {
  return parent.has_photo
    ? <Image alt={parent.name} fetchPriority="high" height={size} loading="eager" src={`/api/family/parent/photo?v=${parent.photo_version}&profile=${encodeURIComponent(parent.id)}`} unoptimized width={size} />
    : <UserRound aria-hidden="true" />;
}
