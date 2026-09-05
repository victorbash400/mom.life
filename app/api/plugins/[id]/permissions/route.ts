import { backend, jsonRequest } from "../../../../lib/backend";
export async function PATCH(request: Request, context: RouteContext<"/api/plugins/[id]/permissions">) { const { id } = await context.params; return backend(`plugins/${encodeURIComponent(id)}/permissions`, await jsonRequest(request,"PATCH")); }
