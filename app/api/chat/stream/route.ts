import { sessionHeaders } from "../../../lib/session";
export async function POST(request: Request) {
  const backendUrl = process.env.MOM_LIFE_BACKEND_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${backendUrl}/api/chat/stream`, { method: "POST", headers: { "Content-Type": "application/json", ...await sessionHeaders() }, body: await request.text(), cache: "no-store", signal: request.signal });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "text/event-stream", "Cache-Control": "no-cache" } });
  } catch {
    return Response.json({ error: "The mom.life backend is unavailable." }, { status: 503 });
  }
}
