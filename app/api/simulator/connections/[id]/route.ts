import { backend } from "../../../../lib/backend";
export async function PUT(_request: Request, context: RouteContext<"/api/simulator/connections/[id]">) { const { id } = await context.params; return backend(`simulator/connections/${encodeURIComponent(id)}`, { method: "PUT" }); }
export async function DELETE(_request: Request, context: RouteContext<"/api/simulator/connections/[id]">) { const { id } = await context.params; return backend(`simulator/connections/${encodeURIComponent(id)}`, { method: "DELETE" }); }
