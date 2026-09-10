import { cookies } from "next/headers";
import { backendOrigin, familyCookie, sameOrigin, sessionCookie, sessionHeaders } from "../../../lib/session";

export async function POST(request: Request) {
  if (!sameOrigin(request)) return Response.json({ error: "Invalid request origin." }, { status: 403 });
  try {
    const response = await fetch(`${backendOrigin}/api/auth/logout`, { method: "POST", headers: await sessionHeaders() });
    if (!response.ok && response.status !== 401) throw new Error("Sign out failed.");
    const cookieStore = await cookies();
    cookieStore.delete(sessionCookie);
    cookieStore.delete(familyCookie);
    return Response.json({ signedOut: true });
  } catch { return Response.json({ error: "Could not sign out. Please try again." }, { status: 503 }); }
}
