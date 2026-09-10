import { cookies } from "next/headers";
import { backendOrigin, familyCookie, sameOrigin, sessionCookie } from "../../../lib/session";

export async function POST(request: Request) {
  if (!sameOrigin(request)) return Response.json({ error: "Invalid request origin." }, { status: 403 });
  try {
    const response = await fetch(`${backendOrigin}/api/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: await request.text(), cache: "no-store" });
    const result = await response.json();
    if (!response.ok) return Response.json({ error: typeof result.detail === "string" ? result.detail : "Check your email and password." }, { status: response.status });
    const cookieStore = await cookies();
    const options = { httpOnly: true, secure: new URL(request.url).protocol === "https:", sameSite: "lax" as const, path: "/", maxAge: result.expires_in };
    cookieStore.set(sessionCookie, result.token, options);
    cookieStore.set(familyCookie, result.family_id, options);
    return Response.json({ signedIn: true });
  } catch { return Response.json({ error: "The account service is unavailable. Please try again." }, { status: 503 }); }
}
