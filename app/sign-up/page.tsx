import { redirect } from "next/navigation";
import { currentSession } from "../lib/session";
import { AuthShell } from "../components/auth/AuthShell";
export default async function SignUp() {
  if (await currentSession()) redirect("/");
  return <AuthShell mode="signup" />;
}
