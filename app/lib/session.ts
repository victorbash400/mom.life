import "server-only";
import { cookies } from "next/headers";

export const sessionCookie = "mom-life-session";
export const backendOrigin = process.env.MOM_LIFE_BACKEND_URL ?? "http://127.0.0.1:8000";
export async function sessionHeaders() {
  const token = (await cookies()).get(sessionCookie)?.value;
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}
export async function currentSession() {
  const headers = await sessionHeaders();
  if (!headers) return null;
  const response = await fetch(`${backendOrigin}/api/auth/session`, { headers, cache: "no-store" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("The account service is unavailable.");
  return response.json() as Promise<{ family_id: string; name: string; demo: boolean }>;
}
export function sameOrigin(request: Request) {
  return request.headers.get("origin") === new URL(request.url).origin;
}
