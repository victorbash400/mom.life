import Image from "next/image";
import { UserRound } from "lucide-react";
import type { PersonProfile } from "../types/dashboard";

export function ParentAvatar({ parent, size }: { parent: PersonProfile; size: number }) {
  return parent.has_photo
    ? <Image alt={parent.name} height={size} src={`/api/family/parent/photo?v=${parent.photo_version}`} unoptimized width={size} />
    : <UserRound aria-hidden="true" />;
}
