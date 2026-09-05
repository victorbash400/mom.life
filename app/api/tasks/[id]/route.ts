import { backend, jsonRequest } from "../../../lib/backend";
export async function PATCH(request: Request, context: RouteContext<"/api/tasks/[id]">) { const { id } = await context.params; return backend(`tasks/${encodeURIComponent(id)}`, await jsonRequest(request, "PATCH")); }
export async function DELETE(_request: Request, context: RouteContext<"/api/tasks/[id]">) { const { id } = await context.params; return backend(`tasks/${encodeURIComponent(id)}`, { method: "DELETE" }); }
