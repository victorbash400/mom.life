import { backend, jsonRequest } from "../../../lib/backend";
export async function PATCH(request: Request, context: RouteContext<"/api/skills/[id]">) { const { id } = await context.params; return backend(`skills/${encodeURIComponent(id)}`, await jsonRequest(request,"PATCH")); }
