import { FamilyProvider } from "./components/FamilyProvider";
import { backend } from "./lib/backend";
import { redirect } from "next/navigation";
import { currentSession } from "./lib/session";
import { MomLifeShell } from "./components/MomLifeShell";

export default async function Home() {
  if (!await currentSession()) redirect("/sign-in");
  const response = await backend("family");
  if (!response.ok) throw new Error("Could not load your family.");
  return <FamilyProvider initial={await response.json()}><MomLifeShell /></FamilyProvider>;
}
