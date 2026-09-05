import { backend } from "../../../../lib/backend";
export async function POST(_request: Request, context: RouteContext<"/api/plugins/[id]/authorize">) { const { id } = await context.params; return backend(`plugins/${encodeURIComponent(id)}/authorize`, { method: "POST" }); }
