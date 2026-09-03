const backendUrl = process.env.MOM_LIFE_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function PATCH(request: Request, context: RouteContext<"/api/tasks/[id]">) { const { id } = await context.params; return forward(id, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: await request.text() }); }
export async function DELETE(_request: Request, context: RouteContext<"/api/tasks/[id]">) { const { id } = await context.params; return forward(id, { method: "DELETE" }); }

async function forward(id: string, init: RequestInit) {
  try { const response = await fetch(`${backendUrl}/api/tasks/${encodeURIComponent(id)}`, init); return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" } }); }
  catch { return Response.json({ error: "The mom.life backend is unavailable." }, { status: 503 }); }
}
