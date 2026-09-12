import { FamilyProvider } from "./components/FamilyProvider";
import { backend } from "./lib/backend";
import { redirect } from "next/navigation";
import { MomLifeShell } from "./components/MomLifeShell";

export default async function Home() {
  const response = await backend("family");
  if (response.status === 401) redirect("/sign-in");
  if (!response.ok) throw new Error("Could not load your family.");
  return <FamilyProvider initial={await response.json()}><MomLifeShell /></FamilyProvider>;
}
