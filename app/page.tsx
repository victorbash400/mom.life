import { FamilyProvider } from "./components/FamilyProvider";
import { backend } from "./lib/backend";
import { redirect } from "next/navigation";
import { currentSession, sessionFamily } from "./lib/session";
import { MomLifeShell } from "./components/MomLifeShell";

export default async function Home() {
  let familyId = await sessionFamily();
  if (!familyId) {
    const session = await currentSession();
    if (!session) redirect("/sign-in");
    familyId = session.family_id;
  }
  const response = await backend("family", {}, familyId);
  if (response.status === 401) redirect("/sign-in");
  if (!response.ok) throw new Error("Could not load your family.");
  return <FamilyProvider initial={await response.json()}><MomLifeShell /></FamilyProvider>;
}
