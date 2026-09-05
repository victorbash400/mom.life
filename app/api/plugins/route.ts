const backendUrl = process.env.MOM_LIFE_BACKEND_URL ?? "http://127.0.0.1:8000";
export async function GET() { return forward(`${backendUrl}/api/plugins?family_id=sarah-family`, { cache: "no-store" }); }
async function forward(url: string, init: RequestInit) { try { const response = await fetch(url, init); return new Response(response.body, { status: response.status, headers: { "Content-Type": "application/json" } }); } catch { return Response.json({ error: "The mom.life backend is unavailable." }, { status: 503 }); } }
