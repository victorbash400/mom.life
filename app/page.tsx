import { FamilyProvider } from "./components/FamilyProvider";
import { backend } from "./lib/backend";
import { redirect } from "next/navigation";
import { currentSession } from "./lib/session";
import { MomLifeShell } from "./components/MomLifeShell";

export default async function Home() {
  const session = await currentSession();
  if (!session) redirect("/sign-in");
  const response = await backend("family", {}, session.family_id);
  if (!response.ok) throw new Error("Could not load your family.");
  return <FamilyProvider initial={await response.json()}><MomLifeShell /></FamilyProvider>;
}
