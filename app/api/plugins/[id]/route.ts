import { backend } from "../../../lib/backend";
export async function POST(_request: Request, context: RouteContext<"/api/plugins/[id]">) { const { id } = await context.params; return backend(`plugins/${encodeURIComponent(id)}`, { method: "POST" }); }
export async function DELETE(_request: Request, context: RouteContext<"/api/plugins/[id]">) { const { id } = await context.params; return backend(`plugins/${encodeURIComponent(id)}`, { method: "DELETE" }); }
