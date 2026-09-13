import { sessionHeaders } from "./session";
const backendUrl = process.env.MOM_LIFE_BACKEND_URL ?? "http://127.0.0.1:8000";
export async function backend(path: string, init: RequestInit = {}) {
  const auth = await sessionHeaders();
  if (!auth) return Response.json({ error: "Sign in to continue." }, { status: 401 });
  try {
    const response = await fetch(`${backendUrl}/api/${path}`, { cache: "no-store", ...init, headers: { ...Object.fromEntries(new Headers(init.headers)), ...auth } });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      return Response.json({ error: typeof payload.detail === "string" ? payload.detail : "The request could not be completed." }, { status: response.status });
    }
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json", "Cache-Control": "no-cache", "X-Accel-Buffering": "no", ...(response.headers.get("Content-Disposition") ? { "Content-Disposition": response.headers.get("Content-Disposition")! } : {}) } });
  } catch { return Response.json({ error: "The mom.life backend is unavailable." }, { status: 503 }); }
}
export async function jsonRequest(request: Request, method = "POST"): Promise<RequestInit> {
  const body = await request.text();
  return body ? { method, headers: { "Content-Type": "application/json" }, body } : { method };
}
